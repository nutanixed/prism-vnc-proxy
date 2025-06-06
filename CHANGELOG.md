# Changelog

## [Unreleased] - API Enhancement

### Added
- **Multiple API routes for VM details endpoint**
  - Nutanix v3 API route: `/api/nutanix/v3/vms/{vm_uuid}`
  - Nutanix v1 API route: `/PrismGateway/services/rest/v1/vms/{vm_uuid}`
  - Custom API route: `/api/vm/{vm_uuid}/details`

### Enhanced
- **API compatibility and flexibility**
  - Support for multiple Nutanix API versions
  - Better integration with different API clients
  - Flexible routing options for VM details retrieval

### Technical Details
- Added three new GET routes to the aiohttp application
- All routes point to the same `proxy.vm_details_handler` function
- Maintains backward compatibility with existing functionality
- No breaking changes to current API structure

### Impact
- Improved compatibility with different Nutanix API clients
- Enhanced flexibility for VM details access
- Future-proofed for various API client implementations
- Simplified integration for custom applications