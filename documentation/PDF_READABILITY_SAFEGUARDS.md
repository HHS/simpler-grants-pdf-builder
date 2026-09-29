# PDF readability deployment safeguards

This is the #970 safeguards inventory for the anonymous `/readability/` pilot. It
records what source code establishes and what the *target deployment* still needs
to prove. It is not an approval, an infrastructure change, or a request to enable
the pilot. Keep `HHS_NOFO_PDF_METRICS_PILOT_ENABLED` off in shared environments
until the [pilot release gates](PDF_READABILITY_PILOT.md) and #968 are satisfied.
Use synthetic PDFs only until the security/privacy owners approve a document
classification and handling boundary. Store sensitive configuration, logs, test
artifacts, and approval records in an approved restricted location, not this repo
or a public issue.

Source inspection: Builder commit `a797e02f` and
[HHS/simpler-grants-gov commit `7a4ab951`](https://github.com/HHS/simpler-grants-gov/tree/7a4ab9519c9e20da17ef5ffb78bf1914b1f68fe7)
on 2026-09-24. Terraform describes intended resources; this inspection did
not read Terraform state, the live AWS account, deployed task definitions, or
operational logs. An infrastructure owner must reconcile these observations
with the selected environment before marking a safeguard verified.

| Safeguard | Source observation | Target-deployment evidence / owner decision |
| --- | --- | --- |
| Ingress limits and abuse protection | Builder stops a single upload above 15 MiB and admits one active analysis through a PostgreSQL advisory lock ([upload/slot code](../nofos/nofos/pdf_readability.py)). The [service WAF](https://github.com/HHS/simpler-grants-gov/blob/7a4ab9519c9e20da17ef5ffb78bf1914b1f68fe7/infra/modules/service/waf.tf) attaches managed rules to the ALB, but explicitly allows `SizeRestrictions_BODY`; no `/readability/` rate, burst, or body-size rule appears there. | Infrastructure/security owners: record the actual ingress chain and effective request/body limits, per-client and burst rules, monitoring/alerts, and safe synthetic load evidence. The application bounds are not ingress controls. Choose whether an existing platform control suffices or a narrowly scoped rule is required. |
| Independent route block | The [ALB listener](https://github.com/HHS/simpler-grants-gov/blob/7a4ab9519c9e20da17ef5ffb78bf1914b1f68fe7/infra/modules/service/load_balancer.tf) forwards `/*`; no route-specific block is shown in the inspected service module. The Builder flag provides an application 503 ([view](../nofos/bloom_nofos/views.py)), not an infrastructure backstop. | Infrastructure/incident owners: identify the approved WAF/ALB or other upstream block, its operator and rollback path, then demonstrate that it blocks GET and POST while Django remains reachable elsewhere. Do not test by exposing real documents. |
| Analyzer privilege, credentials, filesystem and egress | The child receives a minimal allow-listed environment, a 15-second parent timeout, and Linux resource ceilings ([runner](../nofos/nofos/pdf_readability.py), [worker](../nofos/nofos/pdf_readability_worker.py)). The [NOFO service](https://github.com/HHS/simpler-grants-gov/blob/7a4ab9519c9e20da17ef5ffb78bf1914b1f68fe7/infra/nofos/service/main.tf) sets `readonly_root_filesystem = false` and passes app secrets into the web task. The [shared ECS task definition](https://github.com/HHS/simpler-grants-gov/blob/7a4ab9519c9e20da17ef5ffb78bf1914b1f68fe7/infra/modules/service/main.tf) declares `/tmp` tmpfs for the container that runs the analyzer; the [task security group](https://github.com/HHS/simpler-grants-gov/blob/7a4ab9519c9e20da17ef5ffb78bf1914b1f68fe7/infra/modules/service/networking.tf) allows outbound TCP 80, 443 and 5432. The [Dockerfile](../Dockerfile) sets a non-root `appuser`. None of this constitutes a separate parser sandbox or proves no network access. | Infrastructure/security owners: inspect the *deployed* task definition, IAM role, secrets, user/capabilities, effective filesystem mounts, network/metadata reachability and parser subprocess behavior. Decide and approve the actual isolation approach; document any required change before enablement. Do not infer containment from the filtered Python environment or resource limits. |
| Upload and temporary-file lifecycle | The runner writes `input.pdf` under a request-scoped `TemporaryDirectory` and closes the upload; normal completion and handled errors clean it up ([runner](../nofos/nofos/pdf_readability.py)). The [ECS task definition](https://github.com/HHS/simpler-grants-gov/blob/7a4ab9519c9e20da17ef5ffb78bf1914b1f68fe7/infra/modules/service/main.tf) declares a 1 GiB `/tmp` tmpfs; whether Fargate applies that declaration must be verified in the deployed runtime. Worker/host termination can interrupt application cleanup, and Django upload buffering also needs review. | Privacy/operations owners: verify actual temporary paths and backing storage, task replacement/stale-file cleanup and retention on success, parser failure, timeout, web-worker kill and task termination. Record the approved cleanup window and evidence without retaining document content. |
| Logs, traces, crash dumps and retention | The pilot runner discards parser stderr and maps failures to fixed public codes ([runner](../nofos/nofos/pdf_readability.py)). However, Builder's [request middleware](../nofos/bloom_nofos/middleware.py) logs the full path **including query string**, and in production the user agent/referrer; unhandled exceptions include message and traceback. Infrastructure source configures [WAF logging and request sampling](https://github.com/HHS/simpler-grants-gov/blob/7a4ab9519c9e20da17ef5ffb78bf1914b1f68fe7/infra/modules/service/waf.tf) and [ECS application logs](https://github.com/HHS/simpler-grants-gov/blob/7a4ab9519c9e20da17ef5ffb78bf1914b1f68fe7/infra/modules/service/application_logs.tf) at 1,827 days; [ALB access logs](https://github.com/HHS/simpler-grants-gov/blob/7a4ab9519c9e20da17ef5ffb78bf1914b1f68fe7/infra/modules/service/access_logs.tf) expire after 2,555 days. | Security/privacy/observability owners: inspect deployed request, WAF, ALB, app, forwarding, tracing and crash-dump pipelines and their access/retention. Specifically test whether a query-string filename or content, referrer, exception, uploaded filename, extracted text or metrics could enter a log. Approve a route-specific handling plan and remediate any leak before enablement. Source retention settings are not proof of effective deployed retention. |

## Required decision record

For each selected environment, the release owner must link restricted, dated
evidence for the rows above and name the application, infrastructure, security,
privacy, operations/incident and support decision-makers. Record the permitted
document classification, audience, isolation and retention decisions, any
exceptions with their approver, and each unresolved gap. An unverified or
unapproved row remains a release blocker. The separate #971 deployment worksheet
covers deployed version/flag, synthetic end-to-end checks and operating handoff;
it should reference this inventory rather than duplicate it.
