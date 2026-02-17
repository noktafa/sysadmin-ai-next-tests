# Test Environment Protocol

## Pre-Test Checklist
- [ ] Cleanup any orphaned droplets from previous runs
- [ ] Verify DigitalOcean token is valid
- [ ] Check cost guard settings

## During Test
- [ ] Document each OS target tested
- [ ] Record test results and any failures
- [ ] Capture logs for debugging

## Post-Test Checklist
- [ ] Destroy all droplets created during test
- [ ] Remove SSH keys created for test
- [ ] Verify no orphaned resources remain
- [ ] Generate and commit test report

## Test Reports

### Report Format
Each test run generates a report in `reports/YYYY-MM-DD_HH-MM-SS.md`

### Report Contents
- Test date and duration
- OS targets tested
- Tests run (passed/failed/skipped)
- Issues encountered
- Cost estimate
- Cleanup confirmation
