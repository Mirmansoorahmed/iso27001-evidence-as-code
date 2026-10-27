import json
import subprocess
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "policies"


def denies(hcl: str) -> list[str]:
    path = Path("/tmp/eac-rego-case.tf")
    path.write_text(textwrap.dedent(hcl).lstrip("\n"))
    proc = subprocess.run(
        ["conftest", "test", "-p", str(POLICY), "-o", "json", "--no-color", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode in (0, 1) and proc.stdout.strip(), proc.stderr or proc.stdout
    result = json.loads(proc.stdout)[0]
    return [item["msg"].split(":", 1)[0] for item in result.get("failures") or []]


GOOD_STORAGE = """
locals {
  location = "germanywestcentral"
  tags_confidential = {
    data_classification = "confidential"
    owner               = "payments-platform"
    environment         = "dev"
  }
}
resource "azurerm_storage_account" "payments" {
  name     = "st"
  location = local.location
  resource_group_name = "rg"
  account_tier = "Standard"
  account_replication_type = "GZRS"
  tags = local.tags_confidential
}
"""


def test_locals_are_resolved_and_a_good_storage_account_is_quiet():
    assert denies(GOOD_STORAGE) == []


def test_missing_tags_and_a_non_eu_region_fail():
    found = set(denies("""
    resource "azurerm_storage_account" "payments" {
      name     = "st"
      location = "eastus"
      resource_group_name = "rg"
      account_tier = "Standard"
      account_replication_type = "LRS"
    }
    """))
    assert "nordpay.tags.data_classification" in found
    assert "nordpay.tags.owner" in found
    assert "nordpay.region.eu_only" in found


def test_confidential_key_vault_needs_purge_protection():
    bad = denies("""
    resource "azurerm_key_vault" "payments" {
      name = "kv"
      location = "germanywestcentral"
      resource_group_name = "rg"
      tenant_id = "00000000-0000-0000-0000-000000000001"
      sku_name = "standard"
      purge_protection_enabled = false
      tags = { data_classification = "confidential", owner = "payments-platform" }
    }
    """)
    assert "nordpay.keyvault.purge_protection_confidential" in bad
    good = denies("""
    resource "azurerm_key_vault" "payments" {
      name = "kv"
      location = "germanywestcentral"
      resource_group_name = "rg"
      tenant_id = "00000000-0000-0000-0000-000000000001"
      sku_name = "standard"
      purge_protection_enabled = true
      tags = { data_classification = "confidential", owner = "payments-platform" }
    }
    """)
    assert "nordpay.keyvault.purge_protection_confidential" not in good


def test_subscription_owner_fails_and_resource_group_owner_does_not():
    bad = denies("""
    resource "azurerm_role_assignment" "standing_owner" {
      scope                = "/subscriptions/00000000-0000-0000-0000-000000000000"
      role_definition_name = "Owner"
      principal_id         = "11111111-1111-1111-1111-111111111111"
    }
    """)
    assert bad == ["nordpay.rbac.no_subscription_owner"]
    good = denies("""
    resource "azurerm_role_assignment" "group_owner" {
      scope                = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-nordpay-prod"
      role_definition_name = "Owner"
      principal_id         = "11111111-1111-1111-1111-111111111111"
    }
    """)
    assert good == []


def test_prod_storage_needs_diagnostics_and_a_vault():
    diag_only = set(denies("""
    resource "azurerm_storage_account" "payments" {
      name = "st"
      location = "germanywestcentral"
      resource_group_name = "rg"
      account_tier = "Standard"
      account_replication_type = "GZRS"
      tags = { data_classification = "confidential", owner = "payments-platform", environment = "prod" }
    }
    resource "azurerm_monitor_diagnostic_setting" "payments" {
      name = "diag"
      target_resource_id = azurerm_storage_account.payments.id
      log_analytics_workspace_id = "/subscriptions/x/resourceGroups/rg/providers/Microsoft.OperationalInsights/workspaces/log"
      metric {
        category = "Transaction"
        enabled  = true
      }
    }
    """))
    assert "nordpay.backup.vault_for_prod" in diag_only
    assert "nordpay.diagnostics.required" not in diag_only

    vault_only = set(denies("""
    resource "azurerm_storage_account" "payments" {
      name = "st"
      location = "germanywestcentral"
      resource_group_name = "rg"
      account_tier = "Standard"
      account_replication_type = "GZRS"
      tags = { data_classification = "confidential", owner = "payments-platform", environment = "prod" }
    }
    resource "azurerm_recovery_services_vault" "backup" {
      name = "rsv"
      location = "germanywestcentral"
      resource_group_name = "rg"
      sku = "Standard"
      tags = { data_classification = "internal", owner = "payments-platform" }
    }
    """))
    assert "nordpay.diagnostics.required" in vault_only
    assert "nordpay.backup.vault_for_prod" not in vault_only


def test_log_analytics_retention():
    short = denies("""
    resource "azurerm_log_analytics_workspace" "sec" {
      name = "log"
      location = "germanywestcentral"
      resource_group_name = "rg"
      sku = "PerGB2018"
      retention_in_days = 30
      tags = { data_classification = "confidential", owner = "payments-platform" }
    }
    """)
    assert "nordpay.logging.retention" in short
    ok = denies("""
    resource "azurerm_log_analytics_workspace" "sec" {
      name = "log"
      location = "germanywestcentral"
      resource_group_name = "rg"
      sku = "PerGB2018"
      retention_in_days = 90
      tags = { data_classification = "confidential", owner = "payments-platform" }
    }
    """)
    assert "nordpay.logging.retention" not in ok
