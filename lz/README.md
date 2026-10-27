# NordPay landing zone

Fictional Azure landing zone for NordPay GmbH, a Berlin payment institution that exists only in this repo. Nothing here is applied. `terraform validate` is as far as the offline demo goes; `plan` needs credentials and is not part of v1.

The Rego policies read HCL literals and `local.*` references. They do not evaluate variables, which is why the region and the tags are locals.
