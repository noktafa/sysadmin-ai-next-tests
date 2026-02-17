# sysadmin-ai-next-tests

Integration testing pipeline for [sysadmin-ai-next](https://github.com/noktafa/sysadmin-ai-next). Spins up real DigitalOcean VMs across 6 Linux distributions, deploys sysadmin-ai-next via SSH, and validates:

- Policy engine (OPA integration, local rules)
- Sandbox isolation (Docker/K8s/chroot)
- Plugin system
- Playbook generation (Ansible/Terraform)
- Command recovery
- Cost tracking

## OS Matrix

| Family | Target | Image | Pkg Manager |
|--------|--------|-------|-------------|
| Debian | Ubuntu 24.04 | ubuntu-24-04-x64 | apt |
| Debian | Ubuntu 22.04 | ubuntu-22-04-x64 | apt |
| Debian | Debian 12 | debian-12-x64 | apt |
| RHEL | CentOS Stream 9 | centos-stream-9-x64 | dnf |
| RHEL | Fedora 42 | fedora-42-x64 | dnf |
| RHEL | AlmaLinux 9 | almalinux-9-x64 | dnf |

## Setup

```bash
pip install -r requirements.txt
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DIGITALOCEAN_TOKEN` | Yes | DigitalOcean API token |
| `OPENAI_API_KEY` | No | Enables OpenAI API tests |
| `OPA_URL` | No | OPA server URL for policy tests |
| `MAX_TEST_DROPLETS` | No | Max concurrent droplets (default: 6) |
| `MAX_SESSION_MINUTES` | No | Session timeout (default: 60) |

## Running Tests

```bash
# Run all integration tests
python run_tests.py integration

# Run specific test group
pytest tests/integration/test_policy.py -v

# Build pre-baked snapshots (faster subsequent runs)
python scripts/build_snapshots.py
```

## Project Structure

```
sysadmin-ai-next-tests/
├── infra/                  # Infrastructure code
│   ├── droplet_controller.py
│   ├── ssh_driver.py
│   ├── os_matrix.py
│   └── guardrails.py
├── tests/integration/      # Test suites
│   ├── test_connectivity.py
│   ├── test_policy.py
│   ├── test_sandbox.py
│   ├── test_plugins.py
│   ├── test_playbooks.py
│   └── test_cost.py
├── scripts/                # Utilities
│   ├── build_snapshots.py
│   └── cleanup.py
└── run_tests.py           # Test runner
```

## Safety & Cost

- All VMs are ephemeral and tagged (`sysadmin-ai-next-test`)
- Automatic cleanup on test completion
- Emergency cleanup: `python scripts/cleanup.py`
- Estimated cost: ~$0.01 per full test run (6 VMs × 15 min)
