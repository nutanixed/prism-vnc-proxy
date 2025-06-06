# Commit Message

## Title
```
feat: Add multiple API routes for VM details endpoint
```

## Description
```
Enhanced VNC proxy service with multiple API route support:

- Added Nutanix v3 API route: /api/nutanix/v3/vms/{vm_uuid}
- Added Nutanix v1 API route: /PrismGateway/services/rest/v1/vms/{vm_uuid}  
- Added custom API route: /api/vm/{vm_uuid}/details

This enhancement improves compatibility with different Nutanix API clients
and provides flexible routing options for VM details retrieval.

Features: Multiple API endpoint support for better client compatibility
Integration: Works with both v1 and v3 Nutanix API clients
Flexibility: Custom endpoint for simplified VM details access
```

## Files Changed
- `prism_vnc_proxy.py` - Added multiple API routes for VM details

## Testing
- Service starts successfully with new routes
- All existing functionality preserved  
- HTTP server responds correctly on port 8080
- VNC proxy functionality remains intact
- New API endpoints ready for VM details requests