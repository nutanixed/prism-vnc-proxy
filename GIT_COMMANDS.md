# Git Commands for Committing Changes

## Quick Commit (Recommended)
```bash
# Add the main file change
git add prism_vnc_proxy.py

# Commit with the suggested message
git commit -m "feat: Add multiple API routes for VM details endpoint

Enhanced VNC proxy service with multiple API route support:

- Added Nutanix v3 API route: /api/nutanix/v3/vms/{vm_uuid}
- Added Nutanix v1 API route: /PrismGateway/services/rest/v1/vms/{vm_uuid}  
- Added custom API route: /api/vm/{vm_uuid}/details

This enhancement improves compatibility with different Nutanix API clients
and provides flexible routing options for VM details retrieval."

# Push to GitHub
git push origin main
```

## Alternative: Add Documentation Files Too
```bash
# Add all changes including documentation
git add prism_vnc_proxy.py CHANGELOG.md

# Commit with message
git commit -m "feat: Add multiple API routes for VM details endpoint

Enhanced VNC proxy service with multiple API route support:

- Added Nutanix v3 API route: /api/nutanix/v3/vms/{vm_uuid}
- Added Nutanix v1 API route: /PrismGateway/services/rest/v1/vms/{vm_uuid}  
- Added custom API route: /api/vm/{vm_uuid}/details

This enhancement improves compatibility with different Nutanix API clients
and provides flexible routing options for VM details retrieval."

# Push to GitHub
git push origin main
```

## Check Status Before Committing
```bash
# See what files have changed
git status

# See the exact changes
git diff prism_vnc_proxy.py

# See staged changes
git diff --cached
```

## Clean Up Documentation Files (Optional)
```bash
# Remove the temporary documentation files if you don't want them in the repo
rm COMMIT_MESSAGE.md TECHNICAL_CHANGES.md GIT_COMMANDS.md
```