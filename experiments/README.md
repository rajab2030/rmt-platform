# Experiments

Exploratory studies. **Nothing here is part of RMT's Core or any shipped
domain**, nothing here is imported by the backend, and none of it is needed to
run RMT or the [quickstart](../quickstart/README.md).

They test the Master Control Room (MCR) supervisory idea behind RMT: that no
consequential state change can happen without passing through one controlled
mutation boundary. See
[`docs/MCR_ARCHITECTURAL_PRINCIPLE.md`](../docs/MCR_ARCHITECTURAL_PRINCIPLE.md).

| Directory | What it is |
|---|---|
| [`mcr/`](mcr/) | Experiment 1: four tests of the supervisory boundary in an isolated simulated environment. Evidence in `evidence/`. |
| [`mcr2/`](mcr2/) | Experiment 2, "total supervisory boundary": tests T1–T5. Evidence in `evidence/`. |
| [`mcr3/`](mcr3/) | Experiment 3, an adversarial campaign (T1–T14) that tries to bypass the boundary. Results and findings in [`report.md`](mcr3/report.md). |
| [`mcr2_banking/`](mcr2_banking/) | A simulated banking risk-control boundary for outbound transfer intents. No real payment rail. See its [README](mcr2_banking/README.md). |

Results here are evidence about the specific simulations, not guarantees about
RMT. RMT's actual guarantees are in
[`docs/RMT_GUARANTEES.md`](../docs/RMT_GUARANTEES.md).
