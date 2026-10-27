# Held-out set

[TerraGoat](https://github.com/bridgecrewio/terragoat) (Bridgecrew, Apache-2.0) is fetched at test time at commit `729f8da62c6a85ce4af5ad3d123de97776d954c4`. It is not vendored.

`terragoat-expected.yaml` is the ground truth I wrote by reading that Terraform, not by copying scanner output. The technical half is the adopted Checkov rules. The NordPay half is our own Rego, scored separately because TerraGoat was not written to NordPay's tag and region rules.
