//
// Copyright (c) 2016 Nutanix Inc. All rights reserved.
//
// This encapsulates the controller logic for accessing a VM remote console
// GUI.
//
// Original code adapted from:
// https://github.com/kanaka/noVNC/blob/master/vnc_auto.html
//
// noVNC library:
// https://github.com/kanaka/noVNC
//

(function (global) {

  'use strict';

  // Constants
  // ----------
  // This object encapsulates all constants used in the app
  //
  var Constants = {
    DOM_CONTAINER_ID: 'console',
    RETRY_CONN_INTERVAL_MS: 5000,
    V3_API_ROOT: '/api/nutanix/v3/',
    V2_API_ROOT: '/PrismGateway/services/rest/v2.0/',
    V1_API_ROOT: '/PrismGateway/services/rest/v1/',
    V08_API_ROOT: '/api/nutanix/v0.8/',
    VM_POWER_STATE: {
      ON            : 'on',
      OFF           : 'off',
      SUSPEND       : 'suspend',
      PAUSE         : 'pause',
      RESUME        : 'resume',
      CYCLE         : 'powercycle',
      RESET         : 'reset',
      ACPI_SHUTDOWN : 'acpi_shutdown',
      ACPI_REBOOT   : 'acpi_reboot'
    },
    LOCAL_STORAGE_KEYMAP: 'keymap',
    LOCAL_IDLE_TIME: 'nutanix_ui_idle_time',
    AUTO_RECONNECT_INTERVAL_MS: 30000,
    HYPERVISOR_TYPE: {
      AHV: 'kKvm',
      ESX: 'kVMware',
      XEN: 'kXen'
    },
    TASK_STATUS: {
      V2: {
        SUCCESS: 'succeeded',
        FAIL: 'failed'
      }
    },
    // Rendering the view within the Prism UI.
    MODE_ATTACHED: 'attached',
    // Rendering the view in it's own browser window.
    MODE_DETACHED: 'detached',
    // Console feature IDs. These can be used to toggle support for a particular
    // feature if it is not universally supported.
    FEAT: {
      MOUNT_ISO: 'mount_iso'
    },
    // noVNC console states
    CONSOLE_STATE: {
      NORMAL        : 'normal',
      FAILED        : 'failed',
      DISCONNECTED  : 'disconnected',
      FATAL         : 'fatal',
      LOADED        : 'loaded'
    },
    // Host environment of vm
    HOST_ENV: {
      PE: 'pe',
      PC: 'pc',
      SSP: 'ssp',
      XI: 'xi'
    }
  };

  var $ = global.$;

  // Util
  // ----
  // Common app utils
  //
  var Util = {
    // Gets the value of a URL parameter
    getUrlParameter: function (sParam) {
      var sPageURL = global.location.search.substring(1);
      var sURLVariables = sPageURL.split('&');
      for (var i = 0; i < sURLVariables.length; i++) {
        var sParameterName = sURLVariables[i].split('=');
        if (sParameterName[0] === sParam) {
          return sParameterName[1];
        }
      }
    },

    // Gets the VM ID by parsing the URL
    getVmId: function () {
      return this.getUrlParameter('uuid');
    },

    // Gets the previously saved keyboard layout (if any) from local storage
    getPersistedKeyboardLayout: function () {
      if (global.localStorage &&
        typeof global.localStorage.getItem !== 'undefined') {
        return global.localStorage.getItem(Constants.LOCAL_STORAGE_KEYMAP);
      }
    },

    // Get the host environment of vm
    getHostEnv: function() {
      if (this.getUrlParameter('uhura')) {
        return Constants.HOST_ENV.PE;
      } else if (this.getUrlParameter('isXi')) {
        return Constants.HOST_ENV.XI;
      } else if (this.getUrlParameter('noV1Access')) {
        return Constants.HOST_ENV.SSP;
      } else {
        return constants.HOST_ENV.PC;
      }
    },

    // Create URL for the react console
    createNewConsoleURL: function() {
      const vmId = this.getVmId();
      const env = this.getHostEnv();
      const mode = this.getUrlParameter('attached') === 'true'
        ? Constants.MODE_ATTACHED
        : Constants.MODE_DETACHED;
      return '/console/vnc/#/vm/' + vmId + '?env=' + env + '&mode=' + mode;
    },

    // Save the user selected keyboard layout to local storage
    persistKeyboardLayout: function (kbd) {
      if (global.localStorage &&
        typeof global.localStorage.setItem !== 'undefined') {
        global.localStorage.setItem(Constants.LOCAL_STORAGE_KEYMAP, kbd);
      }
    },

    // Throttle function to update ui_idle_time in localstorage
    // for mouse/keyboard events in each window time.
    throttle: function(callback, wait, context) {
      context = context || this;
      var timeout = null,
          previous = 0;

      var later = function() {
            previous = Date.now();
            timeout = null;
            callback.apply(context);
          };

      return function() {
        var now = Date.now();
        if(!previous) {
          previous = now;
        }
        var remaining = wait - (now - previous);
        if(remaining <= 0 || remaining > wait) {
          if(timeout) {
            clearTimeout(timeout);
            timeout = null;
          }
          previous = now;
          callback.apply(context);
        } else if(!timeout) {
          timeout = setTimeout(later, remaining);
        }
      };
    }
  };

  // Return a handler for checking the status of a v2 task.
  var getV2TaskHandler = function(pollId, options) {
    return function(response) {
      var status = (response.progress_status || '').toLowerCase();
      if (status === Constants.TASK_STATUS.V2.SUCCESS) {
        clearInterval(pollId);
        options.success();
      } else if (status ===  Constants.TASK_STATUS.V2.FAILED) {
        clearInterval(pollId);
        options.error('Task failed to complete');
      }
    }
  };
  // Return a handler for checking the status of a v3 task.
  var getV3TaskHandler = function() {
    // TODO: Populate this if you want to watch a v3 task.
  }

  // Simple data model for dealing with the VM API response.
  var VmModel = function(data) {
    data = data || {};

    return {
      getId: function() {
        return data.uuid;
      },

      // Return a boolean indicating if there is a CD-ROM drive currently
      // attached to the VM.
      hasCdrom: function() {
        return !!this.getCdroms().length;
      },

      // Return an array of CD-ROM drives attached to the VM.
      getCdroms: function() {
        return this.getDisks().filter(function(disk) {
          return disk.is_cdrom;
        });
      },

      // Find the VM disk by it's identifier.
      getDiskById: function(id) {
        var disks = this.getDisks();
        for (var i = 0; i < disks.length; i++) {
          var disk = disks[i];
          if (disk.disk_address.disk_label === id) {
            return disk;
          }
        }
      },

      // Return and array of disks attached to the VM.
      getDisks: function() {
        return data.vm_disk_info || [];
      },

      // Return a new copy of the disk updated to have the given image attached
      // to it.
      attachIso: function(diskId, image) {
        var disk = this.getDiskById(diskId);

        return {
          disk_address: {
            device_index: disk.disk_address.device_index,
            device_bus: disk.disk_address.device_bus
          },
          flash_mode_enabled: disk.flash_mode_enabled,
          is_cdrom: true,
          is_empty: false,
          vm_disk_clone: {
            disk_address: {
              vmdisk_uuid: image.vm_disk_id
            },
            minimum_size: image.vm_disk_size
          }
        }
      }
    }
  }

  // DataManager
  // -----------
  // Handles the interchange of data between the app and the
  // server via the REST API
  //
  var DataManager = {
    // The URL param for proxy cluster UUID
    PARAM_PROXY_CLUSTER_UUID: 'proxyClusterUuid',

    // Header to track the client type for API calls
    CLIENT_TRACKING_HEADER: 'X-Nutanix-Client-Type',

    // The client id for tracking
    CLIENT_ID: 'ui',

    // Cluster UUID to include in API requests. This is used when proxying
    // requests through PC to PE.
    proxyClusterUuid: null,

    initialize: function() {
      var _this = this;
      $.ajaxPrefilter(function (options, originalOptions, jqXhr) {
        jqXhr.setRequestHeader(_this.CLIENT_TRACKING_HEADER, _this.CLIENT_ID);
      });
    },

    // Gets the session info from the API
    getSessionInfo: function (success, error, useV3) {

      // Check if we use V3 API from SSP
      if(useV3) {
        var url = Constants.V3_API_ROOT + 'users/me';
      }
      else {
        var url = Constants.V1_API_ROOT + 'users/session_info';
      }
      $.get(url).done(success).fail(error);
    },

    // Set the proxy
    setProxyCluster: function(uuid) {
      this.proxyClusterUuid = uuid;
    },

    // Return the appropriate base url for the given API version.
    getBaseUrl: function(version) {
      switch(version) {
        case 'v0.8':
          return Constants.V08_API_ROOT;
        case 'v1':
          return Constants.V1_API_ROOT;
        case 'v2':
          return Constants.V2_API_ROOT;
        default:
          return Constants.V3_API_ROOT;
      }
    },

    // Sends a GET request to the server.
    get: function(url, query) {
      query = query || {};

      // Inject the proxy cluster into the query params if needed.
      if (this.proxyClusterUuid) {
        query[this.PARAM_PROXY_CLUSTER_UUID] = this.proxyClusterUuid;
      }

      return $.get(url, query);
    },

    // Sends a PUT request to the server.
    put: function(url, data) {
      // Inject the proxy cluster into the query params if needed.
      if (this.proxyClusterUuid) {
        var query = {};
        query[this.PARAM_PROXY_CLUSTER_UUID] = this.proxyClusterUuid;
        url += '?' + $.param(query);
      }

      return $.ajax({
        type: 'PUT',
        url: url,
        contentType: 'application/json',
        data: JSON.stringify(data)
      });
    },

    // Gets the VM details for a VM using the requested api version.
    //
    // @param {string} vmId - UUID of the VM to fetch.
    // @param {string} version - API version to use.
    getVm: function(vmId, version) {
      var baseUrl = this.getBaseUrl(version);
      var url = baseUrl + 'vms/' + vmId;
      var queryParams = { include_vm_disk_config: true };

      return DataManager.get(url, queryParams);
    },

    // Gets the VM details from the REST API.
    getVmDetails: function (vmId, success, error, noV1Access) {
      this.getVm(vmId, noV1Access ? 'v3' : 'v1').done(success).fail(error);
    },

    // Simple poller used to wait for task completion.
    //
    // @param options.interval - Polling interval in milliseconds.
    // @param options.timeout - Number of intervals to poll for.
    // @param options.success - Callback called on task success.
    // @param options.error - Callback called on task failure.
    waitForTask: function(taskId, options) {
      var timeout = options.timeout || 10;      // Default 5 minutes
      var interval = options.interval || 30000; // Default 30 seconds
      var iterations = 0;
      var version = options.apiVersion || 'v3';
      var getHandler = (version === 'v3') ? getV3TaskHandler : getV2TaskHandler;

      var url = DataManager.getBaseUrl(version) + 'tasks/' + taskId
      var pollId = setInterval(function() {
        // Keep checking the task until the polling timeout.
        if (iterations < timeout) {
          DataManager.get(url)
            .done(getHandler(pollId, options))
            .fail(function() {
              clearInterval(pollId);
              error();
            });
          iterations++
        } else {
          clearInterval(pollId);
          options.error('Operation timed out');
        }
      }, interval);
    },

    // Get the available images on the cluster.
    getImages: function(success, error) {
      var url = DataManager.getBaseUrl('v2') + 'images';
      DataManager.get(url).done(success).fail(error);
    },

    // Update the disk configuration for the VM.
    updateDisks: function(vmId, data, success, error) {
      var url = DataManager.getBaseUrl('v2') + 'vms/' + vmId + '/disks/update';

      DataManager.put(url, data)
        .then(function(response) {
          // The disk attach operation shouldn't take very long to complete so
          // we will check the status of the task every second for up to
          // 2 minutes.
          DataManager.waitForTask(response.task_uuid, {
            interval: 1000,
            timeout: 120,
            apiVersion: 'v2',
            success: success,
            error: error
          });
        })
        .fail(function (response, status, jqXHR) {
          global.console && global.console.log('Failed to mount image');
          error(response, status, jqXHR);
        });
    },

    // Sets the power state for the VM by invoking the REST API
    setPowerState: function (vmId, clusterId, useUhura,
                             action, success, error) {
      var vmMgmtApiRoot = Constants.V08_API_ROOT;
      if (useUhura) {
        vmMgmtApiRoot = Constants.V2_API_ROOT;
      }
      var url = vmMgmtApiRoot + 'vms/' + vmId + '/set_power_state';
      if (clusterId) {
        url += '?' + this.PARAM_PROXY_CLUSTER_UUID + '=' + clusterId;
      }
      $.ajax({
        type: 'POST',
        url: url,
        data: JSON.stringify({
          transition: action
        }),
        contentType: 'application/json'
      }).done(success).fail(error);
    }
  };

  // ConsoleManager
  // --------------
  // This class encapsulates the VM console session
  //
  var ConsoleManager = function (options) {
    this.rfb = null;
    this.consoleState = null;

    // Common options
    this.hypervisorType = options.hypervisorType;
    this.host = options.host;
    this.port = options.port;
    this.password = options.password;
    this.path = options.path;
    this.encrypt = options.encrypt;
    this.targetEl = options.targetEl;
    this.onUpdateState = options.onUpdateState;
    this.skipVncHandshake = options.skipVncHandshake;

    this.keymaps = global.scancode_mapper.list();
  };

  // Starts the noVNC session
  ConsoleManager.prototype._startNoVncSession = function () {
    // added by harjeet.singh@nutanix.com to add custom header.
    // for ENG-112665
    // WebSocket will not allow any custom headers otherwise.
    document.cookie = 'X-Nutanix-Client-Type=ui; path=/';

    global.WebUtil.init_logging(
      global.WebUtil.getQueryVar('logging', 'warn'));

    this.rfb = new global.RFB({
      'target'      : this.targetEl,
      'encrypt'     : this.encrypt,
      'repeaterID'  : this.repeaterId || '',
      'skipVncHandshake': this.skipVncHandshake,
      'true_color'  : this.trueColor || true,
      'local_cursor': this.localCursor || true,
      'shared'      : this.shared || true,
      'view_only'   : this.viewOnly || false,
      'updateState' : this.onUpdateState,
      'onPasswordRequired': this.onPasswordRequired
    });

    this.connect();
  };

  // Returns the list of supported keyboard layout ids
  ConsoleManager.prototype.getSupportedKeymaps = function () {
    return this.keymaps || [];
  };

  // Starts the remote VM session
  ConsoleManager.prototype.startSession = function () {
    this._startNoVncSession();
  };

  // Makes the connection to the remote VM
  ConsoleManager.prototype.connect = function () {
    this.rfb.connect(this.host, this.port, this.password, this.path);
  };

  // Sets the password to establish connection
  ConsoleManager.prototype.setPassword = function (password) {
    if (this.rfb) {
      this.rfb.sendPassword(password);
    }
  };

  // Set the keyboard layout for the VM console
  ConsoleManager.prototype.setKeyboardLayout = function (kbd) {
    if (this.keymaps.indexOf(kbd) < 0) {
      kbd = null;
    }
    if (this.rfb) {
      global.scancode_mapper.layout = kbd;
    }

    return kbd;
  };

  // Gets the state of the console
  ConsoleManager.prototype.getConsoleState = function () {
    return this.consoleState;
  };

  // Sets the state of the console
  ConsoleManager.prototype.setConsoleState = function (consoleState) {
    this.consoleState = consoleState;
  };

  // Sends Ctrl+Alt+Del key combination to the remote VM
  ConsoleManager.prototype.sendCtrlAltDel = function () {
    if (this.rfb) {
      this.rfb.sendCtrlAltDel();
    }
  };

  // Ends the VM console session by disconnection
  ConsoleManager.prototype.endSession = function () {
    if (this.rfb) {
      this.rfb.disconnect();
    }
  };


  // VmConsoleView
  // -------------
  // This is the controller class for the app view
  //

  // @constructor
  var VmConsoleView = function () {
    this.hypervisorType = null;
    this.conMan = null;
    this.vmName = null;
    this.vmId = Util.getVmId();
    this.clusterId = Util.getUrlParameter('clusterId');
    this.dataLoaded = false;
    this.uhuraVm = (Util.getUrlParameter('uhura') === 'true');
    this.useV3 = (Util.getUrlParameter('useV3') === 'true');
    this.isXi = (Util.getUrlParameter('isXi') === 'true');
    this.noV1Access = (Util.getUrlParameter('noV1Access') === 'true');
    this.renderMode = (Util.getUrlParameter('attached') === 'true')
      ? Constants.MODE_ATTACHED
      : Constants.MODE_DETACHED;
    this.disabledFeats = [];

    DataManager.setProxyCluster(this.clusterId);
  };

  // Fetches the data from the API and renders the app
  VmConsoleView.prototype.loadDataAndRender = function () {
    var _this = this;
    var vmId = _this.vmId;
    var onError = function() {
      _this.showStatus('Error fetching VM details');
    };

    this.showStatus('Fetching VM info...');
    this.runKbdSupportTest();

    var options = this.getQueryParamOptions();
    if ((options.hypervisorType && options.vmName &&
         options.controllerVm) || options.internalMode) {
      this.startConsoleSession(options);
    } else {
      DataManager.getVmDetails(vmId, function(res) {
        // Since we cannot use the v2 APIs for CVMs, features depending on this
        // must be disabled. If we're unable to determine it's a CVM assume it
        // is for safety.
        var isCvm = res.controllerVm || !res.hasOwnProperty('controllerVm');
        if (isCvm) {
          _this.disabledFeats.push(Constants.FEAT.MOUNT_ISO);
          _this.startConsoleSession(res);
          return;
        }

        // Attempt to fetch the vm disk information required for the mount
        // iso feature.
        DataManager.getVm(vmId, 'v2', { include_vm_disk_config: true })
          .then(function(v2res) {
            _this.vm = VmModel(v2res);
            _this.startConsoleSession(res);
          })
          .fail(function() {
            // If the v2 vm fetch failed for some reason then just disable the
            // mount iso feature and proceed.
            _this.disabledFeats.push(Constants.FEAT.MOUNT_ISO);
            _this.startConsoleSession(res);
          });

      }, onError, this.noV1Access);
    }
  };

  // Starts the VM console session
  VmConsoleView.prototype.startConsoleSession = function (response,
                                                          status,
                                                          jqXHR) {
    this.hypervisorType = response.hypervisorType;

    if (this.noV1Access && this.useV3) {
      this.vmName = response && response.status && response.status.name;
    } else {
      this.vmName = response.vmName;
    }

    this.dataLoaded = true;
    var _this = this;
    var powerButtonEl = $('#powerOffActionsButton');

    this.showStatus('Connecting to: ' + this.vmName);

    var options = this.getQueryParamOptions();
    options.hypervisorType = this.hypervisorType;

    global.Util.load_scripts(['base64.js', 'websock.js', 'des.js',
      'keysymdef.js', 'keyboard.js', 'input.js', 'display.js',
      'jsunzip.js', 'rfb.js']);

    options.skipVncHandshake =
      (this.hypervisorType === Constants.HYPERVISOR_TYPE.ESX);
    options.targetEl = global.$D('noVNC_canvas');
    options.onUpdateState = this.updateStateNoVnc.bind(this);
    options.onPasswordRequired = this.showPasswordPrompt.bind(this);

    if (response.controllerVm === false) {
      powerButtonEl.removeClass('disabled')
        .attr('title', powerButtonEl.attr('data-tooltip'));
    } else {
      powerButtonEl
        .attr('title', powerButtonEl.attr('data-disabled-tooltip'));
    }

    // For pure v3 users (no access to v1), we hide the power button to avoid
    // confusion until we integrate power actions in v3 context here. For now
    // we just hide it.
    if (this.noV1Access) {
      $('#powerOffActionsButton').hide();
    }

    global.onscriptsload = function () {
      _this.render();

      _this.conMan = new ConsoleManager(options);
      _this.conMan.startSession();

      _this.initKeyboardLayout();
      if (!options.internalMode) {
        _this.startSessionChecker();
      }
    };
  };

  // Update ui_idle_time in localstorage to sync with Prism web console
  // and track activities.
  VmConsoleView.prototype.updateIdleTime = Util.throttle(function() {
    global.localStorage[Constants.LOCAL_IDLE_TIME] = Date.now();
  }, 1000);

  // Renders the view
  VmConsoleView.prototype.render = function () {
    var _this = this;
    global.$('body').on('mouseover click keydown', this.updateIdleTime);

    // Show link to react console if user is using the old console
    if (localStorage.getItem('nutanix_use_rvnc') === 'false') {
      $('.action-link')
        .attr('href',  Util.createNewConsoleURL())
        .show();
    }

    // Toggle UI feature visibility based on support.
    $('#action-mount-iso').toggle(
      this.isFeatSupported(Constants.FEAT.MOUNT_ISO));

    if (!this.dataLoaded) {
      // Change the style if this is attached mode or not
      if (this.renderMode === Constants.MODE_ATTACHED) {
        // This means that VNC is running inside Prism UI
        $('body').addClass('mode_attached');

        // If attached mode, this means we show the launch new window
        // button
        $('#launch_new_window').
          show().
          on('click', _this.launchNewWindow.bind(_this));

        // Hide other elements in attached mode
        $('#noVNC_status').css('visibility', 'hidden');
      } else {
        // Show the power off action button
        $('#powerOffActionsButton').
          show().
          on('click', _this.onPowerButtonClick.bind(_this));

        // noVNC is capturing mouse/keyboard events on window.document by
        // default, so we need to trap input event in the popup.
        // An alternative is to configure noVNC to capture on #noVNC_canvas
        // only. Might be needed for more complex menu.
        $('#dialog-form')
          .on('click keyup keydown keypress', function(e) {
            e.stopPropagation();
          });
      }

      // Style the dropdown
      $('select:not(".browser-select")').fancySelect({ type: 'select' });

      this.loadDataAndRender();
    } else {
      // Enable mount ISO action if possible.
      if (this.isFeatSupported(Constants.FEAT.MOUNT_ISO)) {
        $('#action-mount-iso').show();

        if (this.vm && this.vm.hasCdrom()) {
          // Register action handler.
          $('#action-mount-iso').on('click',
            this.renderMountIsoForm.bind(this));
        } else {
          // If the feature is supported but there are no CD-ROM drives available
          // then we need to disable it and let the user know why via tooltip.
          $('#action-mount-iso')
            .attr('title', 'No available CD-ROM drives.')
            .addClass('disabled');
        }
      }

      // Attach the event handlers
      $('#sendCtrlAltDelButton').on('click', this.sendCtrlAltDel.bind(this));
      $('#vm_screenshot').on('click', this.vmScreenshot.bind(this));

      this.showVmNameInStatus();
      global.document.title = unescape(this.vmName);
    }
  };

  // Return a boolean indicating if the given feature is supported on this
  // environment.
  VmConsoleView.prototype.isFeatSupported = function(featId) {
    if (featId === Constants.FEAT.MOUNT_ISO) {
      // This feature depends on v1/v2 APIs so disable it for users who do
      // not have access to these. It is also not supported when the console is
      // rendered within the Prism UI since the user will have all VM update
      // actions available to them in that case.
      return this.dataLoaded && !this.noV1Access &&
        this.disabledFeats.indexOf(Constants.FEAT.MOUNT_ISO) === -1 &&
        this.renderMode === Constants.MODE_DETACHED;
    }

    // Assume if we don't know about the feature ID that it's not supported.
    return false;
  }

  // Replaces the status to show a friendly VM name
  VmConsoleView.prototype.showVmNameInStatus = function () {
    var statusEl = $('#noVNC_status');
    var originalStatus = statusEl.text();
    var status = originalStatus.replace('QEMU (' + this.vmId +')',
      this.vmName);

    // Handle an edge case to render the correct status message for ESX
    // upon successful connection.
    // @see ENG-196316
    if (this.hypervisorType === Constants.HYPERVISOR_TYPE.ESX) {
      if (originalStatus.indexOf('encrypted') > -1) {
        status = 'Connected (encrypted) to: ' + this.vmName;
      } else if (originalStatus.indexOf('unencrypted') > -1) {
        status = 'Connected (unencrypted) to: ' + this.vmName;
      }
    }
    statusEl.text(status);
  };

  // Initialises the keyboard layout controls
  VmConsoleView.prototype.initKeyboardLayout = function () {
    var keymaps,
        ii,
        _this = this;

    keymaps = this.conMan.getSupportedKeymaps();

    for (ii = 0; ii < keymaps.length; ii++) {
      var opt = global.document.createElement('option');
      opt.value = keymaps[ii];
      opt.text = keymaps[ii];
      global.$D('keymap').add(opt);
    }
    global.$D('keymap').onchange = function () {
      _this.setKeyboardLayout(this.value);
    };

    // Read and set the persisted keymap if available
    var keymap = Util.getPersistedKeyboardLayout();
    if (keymap) {
      $('#keymap').val(keymap).change();
    }

    $('#keymap').trigger('update');
  };

  // Reads the query parameters and initializes the closure vars
  VmConsoleView.prototype.getQueryParamOptions = function () {
    // By default, use the host and port of server that served this file
    var host = global.WebUtil.getQueryVar('host', global.location.hostname);
    var port = global.WebUtil.getQueryVar('port', global.location.port);

    // if port == 80 (or 443) then it won't be present and should be
    // set manually
    if (!port) {
      if (global.location.protocol.substring(0,5) === 'https') {
        port = 443;
      }
      else if (global.location.protocol.substring(0,4) === 'http') {
        port = 80;
      }
    }

    // If a token variable is passed in, set the parameter in a cookie.
    // This is used by nova-novncproxy.
    var token = global.WebUtil.getQueryVar('token', null);
    if (token) {
      global.WebUtil.createCookie('token', token, 1);
    }

    var password = global.WebUtil.getQueryVar('password', '');
    var path = global.WebUtil.getQueryVar('path');

    var clusterId = global.WebUtil.getQueryVar('clusterId', null);
    // path for ESX
    // Note: VNC connections are always proxied through Java Gateway
    // For AHV, the path is vnc/vm/<vm uuid>/proxy?proxyClusterUuid=<uuid>
    // For ESX, the path is vm/console/<vm uuid>/proxy?proxyClusterUuid=<uuid>
    if (this.hypervisorType === Constants.HYPERVISOR_TYPE.ESX) {
      path = 'vm/console/' + this.vmId + '/proxy';
    }

    // Since aplos endpoint is not reliable, both SSP and XI users will use
    // java gateway endpoint for now.
    // @see ENG-181278, ENG-185807
    if (this.noV1Access && this.useV3) {
      path = 'vnc/vm/' + this.vmId + '/proxy';
    }

    // Read the clusterId query param and use it as "proxyClusterUuid"
    // in the websocket request.
    if (clusterId) {
      path += '?' + DataManager.PARAM_PROXY_CLUSTER_UUID + '=' + clusterId;
    }

    if (!host || !port) {
      this.updateStateNoVnc('failed', 'Must specify host and port in URL');
      return;
    }

    var encrypt = global.WebUtil.getQueryVar('encrypt',
      (global.location.protocol === 'https:'));

    var hypervisorType = global.WebUtil.getQueryVar('hypervisorType', null);
    var controllerVm =
      global.WebUtil.getQueryVar('controllerVm', null) === 'true';
    var vmName = global.WebUtil.getQueryVar('vmName', null);

    if (window.location.protocol === 'https:') {
      var internalMode = false;
    } else {
      var internalMode = (
          global.WebUtil.getQueryVar('internalMode', 'false') === 'true');
    }

    return {
      host          : host,
      port          : port,
      token         : token,
      password      : password,
      path          : path,
      clusterId     : clusterId,
      encrypt       : encrypt,
      hypervisorType: hypervisorType,
      controllerVm  : controllerVm,
      vmName        : vmName,
      internalMode  : internalMode
    };
  };

  // Take a screenshot of the VM console
  VmConsoleView.prototype.vmScreenshot = function () {
    if ($('#vm_screenshot').hasClass('disabled')) {
      return;
    }
    var canvas = global.$D('noVNC_canvas');
    var dataURL = canvas.toDataURL('image/png');

    // Move focus to VNC console
    $('#vm_screenshot').blur();

    var image = new Image();
    image.src = dataURL;

    // Delay action to allow time for focus change
    global.setTimeout(function(){
      var newWindow = global.open('');
      newWindow.document.write(image.outerHTML);
    }, 100);
  };

  // Send a Ctrl+Alt+Del to the remote VM
  VmConsoleView.prototype.sendCtrlAltDel = function () {
    this.conMan.sendCtrlAltDel();
  };

  // Mount disk disk image to the VM CD-ROM drive.
  VmConsoleView.prototype.mountIso = function(image, diskId, options) {
    // Attach the desired ISO to the disk.
    var data = { vm_disks: [this.vm.attachIso(diskId, image)] };

    DataManager.updateDisks(this.vm.getId(), data,
      function onSuccess() {
        options.success();
      },
      function onError() {
        options.error('Failed to mount ');
      });
  };

  // Render the mount ISO form modal used for attaching a disk image to a
  // CD-ROM drive on the VM.
  VmConsoleView.prototype.renderMountIsoForm = function() {
    var _this = this;
    var $dialogEl = $('#dialog-mount-disk');
    var $msg = $dialogEl.find('.msg');
    var $content = $dialogEl.find('.content');
    var $selectImage = $content.find('#select-image');
    var $selectDrive = $content.find('#select-cdrom');
    var imageMap = {};
    var modal;

    var onSuccess = function(response) {
      // Only active ISO images are applicable to this operation.
      var images = response.entities.filter(function(image) {
        return (image.image_state === 'ACTIVE' &&
                image.image_type === 'ISO_IMAGE');
      });

      // Bail if there are no images to select since there's nothing for the
      // user to do in this case.
      if (!images.length) {
        $msg.html('No available images.')
        $content.hide();
        return;
      }
      // Reset inputs.
      $selectImage.empty();
      $selectDrive.empty();

      // Populate the available ISOs.
      images.forEach(function(image) {
        imageMap[image.vm_disk_id] = image;
        $selectImage.append(
          '<option value="' + image.vm_disk_id + '">' + image.name + '</option>');
      });
      // Populate the available CD-ROM drives.
      _this.vm.getCdroms().forEach(function(drive) {
        // Disk labels are <bus>.<index> so we use that as the value since
        // vmdisk_uuid is not populated for empty drives.
        var label = drive.disk_address.disk_label;
        // Get the mounted image of the disk.
        let image;
        if (!drive.is_empty) {
          image = imageMap[drive.source_disk_address.vmdisk_uuid];
        }
        var state = drive.is_empty
          ? 'Empty'
          : image && image.name || 'Has Disk';

        $selectDrive.append(
          '<option value="' + label + '">' +
            label + ' - ' + state +
          '</option>');
      });

      // Toggle content visibility.
      $('#action-mount').button('enable');
      $msg.hide();
      $content.show();
    }
    var showMessage = function(msg) {
      $('#action-mount').button('disable');
      $content.hide();
      $msg.html(msg).show();
    }
    var onError = function(msg) {
      msg = msg || 'An unknown error occurred';
      return function _errorHandler() {
        showMessage(msg);
      }
    }

    // Show the mount ISO dialog.
    modal = $dialogEl.dialog({
      resizable: false,
      modal: true,
      draggable: false,
      closeText: '',
      buttons: [
        {
          text: 'Cancel',
          click: function() { modal.dialog('close') }
        },
        {
          id: 'action-mount',
          text: 'Mount',
          disabled: true,
          click: function() {
            var diskId = $selectDrive.val();
            var image = imageMap[$selectImage.val()];
            var imageName = image.name || 'ISO';

            showMessage('Mounting ' + imageName + ' on ' + diskId + '.');

            _this.mountIso(image, diskId, {
              success: function() {
                modal.dialog('close');
                // Fetching VM info again to update 'CD-ROM Drive' section in mount ISO dialog.
                DataManager.getVm(Util.getVmId(), 'v2')
                    .then(function(result) {
                      _this.vm = VmModel(result);
                    });
              },
              error: onError(
                'Failed to mount ' + imageName + ' on ' + diskId + '.')
            });
          }
        },
      ]
    });

    // Render loader and fetch the available images.
    showMessage('Fetching available images...');
    DataManager.getImages(
      onSuccess,
      onError('Failed to fetch available images.'));
  }

  // Send a power signal to the VM when the power button is clicked
  VmConsoleView.prototype.onPowerButtonClick = function () {
    var _this = this;
    if ($('#powerOffActionsButton').hasClass('disabled')) {
      return;
    }

    if (this.conMan.getConsoleState() !== Constants.CONSOLE_STATE.NORMAL) {
      // Power on VM.
      this.showStatus('Powering on VM...');
      DataManager.setPowerState(this.vmId, this.clusterId, this.uhuraVm,
        Constants.VM_POWER_STATE.ON, function () {
          // Try to re-connect after powering on VM
          global.setTimeout(function(){
            _this.conMan.connect();
          }, 2000);
        }, function () {
          _this.showStatus('Failed to set VM power state');
        });
      return;
    }

    // Hide unsupported hypervisor-specific power actions
    if (this.hypervisorType === Constants.HYPERVISOR_TYPE.ESX) {
      $('#dialog-form .power_action.ahv').hide();
    } else {
      $('#dialog-form .power_action.esx').hide();
      // default power action for ahv(kvm) should be guest shutdown
      if (this.hypervisorType === Constants.HYPERVISOR_TYPE.AHV) {
        $('#guest_shutdown').prop('checked',true);
      }
    }

    // Power off/reset VM.
    $('#dialog-form').dialog({
      resizable: false,
      modal: true,
      draggable: false,
      closeText: '',
      buttons: {
        'Cancel': function() {
          $(this).dialog('close');
        },
        'Submit': function() {
          var powerAction;

          switch($('[name=power_off_action]:checked').val()) {
            case 'power_off':
              powerAction = Constants.VM_POWER_STATE.OFF;
              break;
            case 'power_cycle':
              powerAction = Constants.VM_POWER_STATE.CYCLE;
              break;
            case 'reset':
              powerAction = Constants.VM_POWER_STATE.RESET;
              break;
            case 'guest_shutdown':
              powerAction = Constants.VM_POWER_STATE.ACPI_SHUTDOWN;
              break;
            case 'guest_reboot':
              powerAction = Constants.VM_POWER_STATE.ACPI_REBOOT;
              break;
            default:
              powerAction = Constants.VM_POWER_STATE.OFF;
          }

          $('#dialog-form').dialog('close');
          _this.showStatus('Changing VM power state...');
          DataManager.setPowerState(_this.vmId, _this.clusterId, _this.uhuraVm,
            powerAction,
            function () {
              _this.showStatus('VM power state changed successfully');
            }, function () {
              _this.showStatus('Failed to set VM power state');
            });
        }
      }
    });

    // Hide close icon on the dialog
    $('.ui-dialog-titlebar-close').hide();
  };

  // Launch the console in a new window
  VmConsoleView.prototype.launchNewWindow = function () {
    if ($('#launch_new_window').hasClass('disabled')) {
      return;
    }
    var newUrl = global.location.href;
    newUrl = newUrl.replace('attached=true','attached=false');
    var windowOptions = 'toolbar=0,scrollbars=1,location=0' +
      'statusbar=0,menubar=0,resizable=1,width=720,height=452';
    global.open(newUrl, 'VM Console', windowOptions);
  };

  // Handler for noVNC update state event
  VmConsoleView.prototype.updateStateNoVnc = function (rfb,
                                                       state,
                                                       oldstate,
                                                       msg) {
    var s, sb, level, $buttons;
    s = global.$D('noVNC_status');
    sb = global.$D('noVNC_status_bar');
    $buttons =
      $('#launch_new_window, #vm_screenshot, #sendCtrlAltDelButton');
    var _this = this;

    switch (state) {
      case Constants.CONSOLE_STATE.FAILED:
        level = 'error';
        break;
      case Constants.CONSOLE_STATE.FATAL:
        level = 'error';
        break;
      case Constants.CONSOLE_STATE.NORMAL:
        level = 'normal';
        break;
      case Constants.CONSOLE_STATE.DISCONNECTED:
        level = 'normal';
        break;
      case Constants.CONSOLE_STATE.LOADED:
        level = 'normal';
        break;
      default:
        level = 'warn';
        break;
    }

    if (state === Constants.CONSOLE_STATE.NORMAL) {
      $buttons.each(function () {
        var el = $(this);
        el.removeClass('disabled')
          .attr('title', el.attr('data-tooltip'));
      });
      $('#conn-notif').closest('.ui-dialog-content').dialog('close');

      this.resizeWindowToFit();
    } else {
      $buttons.each(function () {
        var el = $(this);
        el.addClass('disabled')
          .attr('title', el.attr('data-disabled-tooltip'));
      });

      // Attempt auto-reconnect
      if (state === Constants.CONSOLE_STATE.DISCONNECTED) {
        global.setTimeout(function () {
          // If not already re-connected by the user
          if (_this.conMan.getConsoleState() !==
              Constants.CONSOLE_STATE.NORMAL) {
            _this.conMan.connect();
          }
        }, Constants.AUTO_RECONNECT_INTERVAL_MS);
      }
    }

    if (typeof(msg) !== 'undefined') {
      sb.setAttribute('class', 'noVNC_status_' + level);
      s.innerHTML = msg;
    }

    // Replace UUID with more friendly VM name
    var name = this.vmName;
    this.showVmNameInStatus(name);
    this.conMan.setConsoleState(state);
  };

  // Resizes the window to fit the contents of the remote VM screen resolution
  VmConsoleView.prototype.resizeWindowToFit = function () {
    // Resize window to fit contents
    // Hat-tip: http://stackoverflow.com/questions/10385768/
    global.resizeTo($(global.document).width() +
      (global.outerWidth -
      global.document.documentElement.clientWidth),
      $(document).height() +
      (global.outerHeight -
      global.document.documentElement.clientHeight)
    );
  };

  // Displays a status message
  VmConsoleView.prototype.showStatus = function (msg) {
    $('#noVNC_status').text(msg);
  };

  // Polls to check whether or not the Prism session is active
  VmConsoleView.prototype.startSessionChecker = function () {
    var _this = this;

    if (this.sessionChecker) {
      return;
    }

    this.sessionChecker = global.setInterval(function () {
      DataManager.getSessionInfo(function () { },
        function (response, status, jqXHR) {
          if (response.status === 401) {
            _this.conMan.endSession();
            global.clearInterval(_this.sessionChecker);
            _this.sessionChecker = null;
          }
        }, _this.useV3);

    }, Constants.AUTO_RECONNECT_INTERVAL_MS);
  };

  // Test for KeyboardEvent.code by firing dummy event
  VmConsoleView.prototype.runKbdSupportTest = function () {
    var _this = this;
    // Step 1: Register event handler
    $('#kbd-test').on('keypress', function (evt) {
      evt.stopPropagation();
      if (evt.originalEvent &&
        typeof evt.originalEvent.code !== 'undefined') {
        // hide the keyboard layout dropdown on Firefox 38+
        $('.kbd-lang').hide();
      } else if (evt.originalEvent &&
        typeof evt.originalEvent.key !== 'undefined' ||
        navigator.userAgent.indexOf('Mac') >= 0 &&
        typeof evt.originalEvent.keyIdentifier !== 'undefined') {
        _this.showKbdSupportWarning(true);
      } else {
        _this.showKbdSupportWarning();
      }
    });

    // Step 2: Fire dummy event; Note: we are not using jQuery since
    // it does not actually fire a DOM event
    try {
      if (typeof KeyboardEvent !== 'undefined') {
        var kbdEvt;
        try {
          kbdEvt = new KeyboardEvent('keypress', { code: 'KeyA' });
        } catch (ieError) {
          kbdEvt = global.document.createEvent('KeyboardEvent');
          kbdEvt.initEvent('keypress', true, true);
        }
        var testEl = global.document.getElementById('kbd-test');
        if (typeof testEl.dispatchEvent === 'function') {
          testEl.dispatchEvent(kbdEvt);
        }
      }
    } catch (e) {
      _this.showKbdSupportWarning();
      global.console && global.console.log('ERROR: Unable to ' +
        'determine keyboard support');
    }
  };

  VmConsoleView.prototype.setKeyboardLayout = function (kbd) {
    kbd = this.conMan.setKeyboardLayout(kbd);
    Util.persistKeyboardLayout(kbd);
  };

  // Show a warning dialog that the current browser might not have
  // full support for keyboard events.
  // @param partialSupport - used to show the proper message, whether
  //  keyboard support is partial or not supported at all
  VmConsoleView.prototype.showKbdSupportWarning = function (partialSupport) {
    var keymap = Util.getPersistedKeyboardLayout(),
        _this = this;

    // Display the popup if no keymap is selected, default counts too.
    if (!keymap) {
      $('#kbd-notif').dialog({
        resizable: false,
        modal: false,
        draggable: false,
        closeText: '',
        dialogClass: partialSupport ? 'partial-support' : 'no-support',
        buttons: {
          'OK': function () {
            $(this).dialog('close');
            // Store the keymap selection
            _this.setKeyboardLayout(global.scancode_mapper.layout);
          }
        }
      });
    }
  };

  // Displays form when noVNC requires a password to connect
  VmConsoleView.prototype.showPasswordPrompt = function () {
    var msg,
        _this = this;
    msg = '<form id="password_form"';
    msg += '  style="margin-bottom: 0px">';
    msg += 'Password Required: ';
    msg += '<input type=password size=10 id="password_input" ';
    msg +=         'class="noVNC_status">';
    msg += '<\/form>';
    global.$D('noVNC_status_bar').setAttribute(
      'class', 'noVNC_status_warn');
    global.$D('noVNC_status').innerHTML = msg;

    $('#password_form').on('submit', function () {
      _this.setPassword(global.$D('password_input').value);
    });
  };

  // Sets the password for the noVNC connection
  VmConsoleView.prototype.setPassword = function (password) {
    this.conMan.setPassword(password);
    return false;
  };

  // Handler for WebSocket close event
  VmConsoleView.prototype.handleWsClose = function (e) {
    var errorDetails = e ? '(error ' + e.code + ')' : '';
    // If the WebSocket didn't CLOSE_NORMAL (code 1000)
    if (!e || e.code > 1000) {
      this.showStatus('Connection closed  ' + errorDetails);
      $('#conn-notif').dialog({
        resizable: false,
        modal: false,
        draggable: false,
        closeText: '',
        buttons: {
          'OK': function () {
            $(this).dialog('close');
          }
        }
      });
    }
  };

  // The reason why we call jquery's ready function is that we need to
  // render the view very quickly.
  $(function() {
    DataManager.initialize();
    var view = new VmConsoleView();

    // Expose this handler as it is called from within rfb.js
    global.NxUtil = global.NxUtil || {};
    global.NxUtil.handleWsClose = view.handleWsClose.bind(view);

    // Render the view
    view.render();
  });

})(window);
