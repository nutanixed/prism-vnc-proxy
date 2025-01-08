var kbdUtil = (function() {
    "use strict";

    var capsLock = false;

    function substituteCodepoint(cp) {
        // Any Unicode code points which do not have corresponding keysym entries
        // can be swapped out for another code point by adding them to this table
        var substitutions = {
            // {S,s} with comma below -> {S,s} with cedilla
            0x218 : 0x15e,
            0x219 : 0x15f,
            // {T,t} with comma below -> {T,t} with cedilla
            0x21a : 0x162,
            0x21b : 0x163
        };

        var sub = substitutions[cp];
        return sub ? sub : cp;
    }

    // Begin Nutanix change
    //
    // For cases in ESX, when the keyboard language at client side
    // is set to non en-us, some special characters are not recognized
    // or result in wrong mapping.
    // One solution is to map all character input back to en-us layout
    // based on the scancode.
    // scancode is the most accurate and immutable property since it
    // directly relates to the physical location on the keyboard.
    // Referencing: http://www.millisecond.com/support/docs/v5/html/viewer.htm#language/scancodes.htm
    var scancodeCharMap = {
      2  : "1",
      3  : "2",
      4  : "3",
      5  : "4",
      6  : "5",
      7  : "6",
      8  : "7",
      9  : "8",
      10 : "9",
      11 : "0",
      12 : "-",
      13 : "=",
      16 : "q",
      17 : "w",
      18 : "e",
      19 : "r",
      20 : "t",
      21 : "y",
      22 : "u",
      23 : "i",
      24 : "o",
      25 : "p",
      26 : "[",
      27 : "]",
      30 : "a",
      31 : "s",
      32 : "d",
      33 : "f",
      34 : "g",
      35 : "h",
      36 : "j",
      37 : "k",
      38 : "l",
      39 : ";",
      40 : "'",
      41 : "`",
      43 : "\\",
      44 : "z",
      45 : "x",
      46 : "c",
      47 : "v",
      48 : "b",
      49 : "n",
      50 : "m",
      51 : ",",
      52 : ".",
      53 : "/",
      71 : "7",
      72 : "8",
      73 : "9",
      74 : "-",
      75 : "4",
      76 : "5",
      77 : "6",
      78 : "+",
      79 : "1",
      80 : "2",
      81 : "3",
      82 : "0"
    };
    // End Nutanix change

    var noncharacterKeysymMap = {
      'Spacebar': 0x20,
      'AltGraph': 0xfe03,
      'Control': 0xffe3,
      'Control_L': 0xffe3,
      'Control_R': 0xffe4,
      'Alt': 0xffe9,
      'Alt_L': 0xffe9,
      'Alt_R': 0xffea,
//      'CapsLock': 0xffe5,
      'Meta_L': 0xffe7,
      'Meta_R': 0xffe8,
      'Meta': 0xffe8,
      'Shift': 0xffe1,
      'Shift_L': 0xffe1,
      'Shift_R': 0xffe2,
      'Super': 0xffeb,
      'Super_L': 0xffeb,
      'Super_R': 0xffec,
      'Backspace': 0xff08,
      'U+0008' : 0xff08,
      'Tab': 0xff09,
      'U+0009': 0xff09,
      'Return': 0xff0d,
      'Enter': 0xff0d,
      'Right': 0xff53,
      'ArrowRight': 0xff53,
      'Left': 0xff51,
      'ArrowLeft': 0xff51,
      'Up': 0xff52,
      'ArrowUp': 0xff52,
      'Down': 0xff54,
      'ArrowDown': 0xff54,
      'PageDown': 0xff56,
      'PageUp': 0xff55,
      'Insert': 0xff63,
      'Del': 0xffff,
      'U+007F': 0xffff,
      'Home': 0xff50,
      'End': 0xff57,
      'ScrollLock': 0xff14,
      'F14': 0xff14,
      'KP_Home': 0xff95,
      'KP_Left': 0xff96,
      'KP_Up': 0xff97,
      'KP_Right': 0xff98,
      'KP_Down': 0xff99,
      'KP_PageUp': 0xff9a,
      'KP_PageDown': 0xff9b,
      'KP_End': 0xff9c,
      'KP_Begin': 0xff9d,
      'KP_Insert': 0xff9e,
      'KP_Del': 0xff9f,
      'F1': 0xffbe,
      'F2': 0xffbf,
      'F3': 0xffc0,
      'F4': 0xffc1,
      'F5': 0xffc2,
      'F6': 0xffc3,
      'F7': 0xffc4,
      'F8': 0xffc5,
      'F9': 0xffc6,
      'F10': 0xffc7,
      'F11': 0xffc8,
      'F12': 0xffc9,
      'PrintScreen': 0xff15,
      'F13': 0xff15,
      'KP_0': 0xffb0,
      'KP_1': 0xffb1,
      'KP_2': 0xffb2,
      'KP_3': 0xffb3,
      'KP_4': 0xffb4,
      'KP_5': 0xffb5,
      'KP_6': 0xffb6,
      'KP_7': 0xffb7,
      'KP_8': 0xffb8,
      'KP_9': 0xffb9,
      'KP_+': 0xffab,
      'KP_.': 0xffae,
      // Begin Nutanix change
      // to make numLockMap work with German keyboard layout
      'KP_,': 0xffae,
      // End Nutanix change
      'KP_/': 0xffaf,
      'KP_*': 0xffaa,
      'KP_-': 0xffad,
      'KP_Enter': 0xff8d,
      'help': 0xff6a,
      'Menu': 0xff67,
      'Print': 0xff61,
      'ModeSwitch': 0xff7e,
//      'NumLock': 0xff7f,
//      'Clear': 0xff7f,
      'Pause': 0xff13,
      'F15': 0xff13,
      'Esc': 0xff1b,
      'Escape': 0xff1b,
      'U+001B': 0xff1b,
      'DeadGrave': 0xfe50,
      'DeadAcute': 0xfe51,
      'DeadCircumflex': 0xfe52,
      'DeadTilde': 0xfe53,
      'DeadMacron': 0xfe54,
      'DeadBreve': 0xfe55,
      'DeadAboveDot': 0xfe56,
      'DeadAbovedot': 0xfe56,
      'DeadDiaeresis': 0xfe57,
      'DeadAboveRing': 0xfe58,
      'DeadAbovering': 0xfe58,
      'DeadAoubleAcute': 0xfe59,
      'DeadAoubleacute': 0xfe59,
      'DeadCaron': 0xfe5a,
      'DeadCedilla': 0xfe5b,
      'DeadOgonek': 0xfe5c,
      'DeadIota': 0xfe5d,
      'DeadVoicedSound': 0xfe5e,
      'DeadSemivoicedSound': 0xfe5f,
      'DeadBelowDot': 0xfe60,
      'DeadBelowdot': 0xfe60,
      'DeadHook': 0xfe61,
      'DeadHorn': 0xfe62,
      'Muhenkan': 0xff22,
      'Katakana': 0xff27,
      'Hankaku': 0xff29,
      'ZenkakuHankaku': 0xff2a,
      'HenkanModeReal': 0xff23,
      'HenkanModeUltra': 0xff3e,
      'KatakanaReal': 0xff25,
      'EisuToggle': 0xff30
    };

    var numLockRemap = {
      'KP_0': 'KP_Insert',
      'KP_1': 'KP_End',
      'KP_2': 'KP_Down',
      'KP_3': 'KP_PageDown',
      'KP_4': 'KP_Left',
      'KP_5': 'KP_Begin',
      'KP_6': 'KP_Right',
      'KP_7': 'KP_Home',
      'KP_8': 'KP_Up',
      'KP_9': 'KP_PageUp',
      'KP_.': 'KP_Del'
    };

    // Begin Nutanix change
    // Numpad re-mapping for IE
    var numpadRemap = {
      'Add'     : 'KP_+',
      'Decimal' : 'KP_.',
      'Divide'  : 'KP_/',
      'Multiply': 'KP_*',
      'Subtract': 'KP_-'
    };
    // End Nutanix change

    var virtualNumLock = true;

    function kpRemap(kp) {
      if (!virtualNumLock && (kp in numLockRemap)) {
        return numLockRemap[kp];
      }
      return kp;
    }

    function getKey(id, loc) {
        switch (loc) {
        case 1: return id + "_L";
        case 2: return id + "_R";
        case 3: return kpRemap("KP_" + id);
        default: return id;
        }
    }

    // Get the most reliable keysym value we can get from a key event
    // Use information from DOM level 3.
    function getKeysym(evt){
        var key;
        var codepoint;
        var keyCode = 0;
        var location = (evt.location !== undefined ?
                        evt.location : evt.keyLocation);

        // For alphanumeric keys, we can trust the keyCode. This allows
        // us to ignore weird OS specific mappings, like how Mac maps
        // Alt+L to @ on German keyboard instead of Alt+Q, but we don't
        // want to send back the scancode for Q when Alt+L is pressed.
        if (evt.keyCode >= 48 && evt.keyCode <= 57 && !location) {
          keyCode = evt.keyCode;
        } else if ((evt.charCode >= 65 && evt.charCode <= 90) ||
                   (evt.charCode >= 97 && evt.charCode <= 122)) {
          // This has the side effect of picking up the correct case so
          // QEMU can do its own CapsLock syncing.
          keyCode = evt.charCode;

          // Remember our CapsLock state for the keyup event.
          var upperCase = keyCode < 97;
          if (upperCase ^ evt.shiftKey) {
            capsLock = true;
          } else if (!upperCase && !evt.shiftKey) {
            capsLock = false;
          } else if (upperCase && evt.shiftKey) {
            // Turns out that on Mac shift+CapsLock still gives you upper case.
          }
        } else if (evt.keyCode >= 65 && evt.keyCode <= 90) {
          keyCode = evt.keyCode;
          if (!(capsLock ^ evt.shiftKey)) {
            // Make it lower case to make QEMU happy.
            keyCode += 32;
          }
        }

        if (keyCode) {
          return keysyms.fromUnicode(keyCode);
        }

        // For non-characters and other weird shit, require DOM-3.
        if (evt.key !== undefined) { // DOM-3 "key"
          key = getKey(evt.key, evt.location);

          // Begin Nutanix change
          var result = {};

          if (key.length === 1 || key === 'Dead') {
            if(key.length === 1) {
              codepoint = key.charCodeAt(0);
              result.keysym = keysyms.fromUnicode(substituteCodepoint(codepoint));
            }
            // Used for ESX only
            var sc = getScancode(evt);
            if(typeof sc !== 'undefined') {
              if (sc in scancodeCharMap) {
                codepoint = scancodeCharMap[sc].charCodeAt(0);
              }
            }
            result.en_keysym = keysyms.fromUnicode(substituteCodepoint(codepoint));
            // End for ESX use
            return result;
          // End Nutanix change
          } else if (key in noncharacterKeysymMap) {
            return keysyms.lookup(noncharacterKeysymMap[key]);
          } else {
            // Begin Nutanix change
            // Remap IE evt.key to normal key for Numpad'/ * - +'
            if(evt.key in numpadRemap) {
              key = numpadRemap[evt.key];
              if (key in noncharacterKeysymMap) {
                return keysyms.lookup(noncharacterKeysymMap[key]);
              }
            } else {
            // End Nutanix change
              console.log("getKeysym: unknown key " + evt.key +
                " location " + evt.location);
            }
          }
        } else if (evt.keyIdentifier !== undefined) { // Deprecated DOM-3
          key = getKey(evt.keyIdentifier, location);

          if (key in noncharacterKeysymMap) {
            return keysyms.lookup(noncharacterKeysymMap[key]);
          } else if (key.substr(0, 2) == "U+") {
            codepoint = parseInt(key.substr(2), 16);
            return keysyms.fromUnicode(substituteCodepoint(codepoint));
          } else {
            console.log("getKeysym: unknown key " + evt.keyIdentifier +
                        " location " + location);
          }
        }

        return null;
    }

    // Maps from DOM-3 KeyboardEvent.code to get the scancode,
    // regardless of keyboard layout or modifier keys.
    var scancodeMap = {
      "Escape": 0x01,
      "Digit1": 0x02,
      "Digit2": 0x03,
      "Digit3": 0x04,
      "Digit4": 0x05,
      "Digit5": 0x06,
      "Digit6": 0x07,
      "Digit7": 0x08,
      "Digit8": 0x09,
      "Digit9": 0x0a,
      "Digit0": 0x0b,
      "Minus": 0x0c,
      "Equal": 0x0d,
      "Backspace": 0x0e,
      "Tab": 0x0f,
      "KeyQ": 0x10,
      "KeyW": 0x11,
      "KeyE": 0x12,
      "KeyR": 0x13,
      "KeyT": 0x14,
      "KeyY": 0x15,
      "KeyU": 0x16,
      "KeyI": 0x17,
      "KeyO": 0x18,
      "KeyP": 0x19,
      "BracketLeft": 0x1a,
      "BracketRight": 0x1b,
      "Enter": 0x1c,
      "ControlLeft": 0x1d,
      "KeyA": 0x1e,
      "KeyS": 0x1f,
      "KeyD": 0x20,
      "KeyF": 0x21,
      "KeyG": 0x22,
      "KeyH": 0x23,
      "KeyJ": 0x24,
      "KeyK": 0x25,
      "KeyL": 0x26,
      "Semicolon": 0x27,
      "Quote": 0x28,
      "Backquote": 0x29,
      "ShiftLeft": 0x2a,
      "Backslash": 0x2b,
      "KeyZ": 0x2c,
      "KeyX": 0x2d,
      "KeyC": 0x2e,
      "KeyV": 0x2f,
      "KeyB": 0x30,
      "KeyN": 0x31,
      "KeyM": 0x32,
      "Comma": 0x33,
      "Period": 0x34,
      "Slash": 0x35,
      "ShiftRight": 0x36,
      "NumpadMultiply": 0x37,
      "AltLeft": 0x38,
      "Space": 0x39,
//      "CapsLock": 0x3a,
      "F1": 0x3b,
      "F2": 0x3c,
      "F3": 0x3d,
      "F4": 0x3e,
      "F5": 0x3f,
      "F6": 0x40,
      "F7": 0x41,
      "F8": 0x42,
      "F9": 0x43,
      "F10": 0x44,
      "ScrollLock": 0x46,
      "Numpad7": 0x47,
      "Numpad8": 0x48,
      "Numpad9": 0x49,
      "NumpadSubtract": 0x4a,
      "Numpad4": 0x4b,
      "Numpad5": 0x4c,
      "Numpad6": 0x4d,
      "NumpadAdd": 0x4e,
      "Numpad1": 0x4f,
      "Numpad2": 0x50,
      "Numpad3": 0x51,
      "Numpad0": 0x52,
      "NumpadDecimal": 0x53,
      "IntlBackslash": 0x56,
      "F11": 0x57,
      "F12": 0x58,
      "NumpadEqual": 0x59,
      "F13": 0x64,
      "F14": 0x65,
      "F15": 0x66,
      "F16": 0x67,
      "F17": 0x68,
      "F18": 0x69,
      "F19": 0x6a,
      "F20": 0x6b,
      "F21": 0x6c,
      "F22": 0x6d,
      "F23": 0x6e,
      "KanaMode": 0x70,
      "IntlRo": 0x73,
      "F24": 0x76,
      "Convert": 0x79,
      "NonConvert": 0x7b,
      "IntlYen": 0x7d,
      "NumpadComma": 0x7e,
      "MediaTrackPrevious": 0x90,
      "MediaTrackNext": 0x99,
      "NumpadEnter": 0x9c,
      "ControlRight": 0x9d,
      "VolumeMute": 0xa0,
      "LaunchApp2": 0xa1,
      "MediaPlayPause": 0xa2,
      "MediaStop": 0xa4,
      "VolumeDown": 0xae,
      "VolumeUp": 0xb0,
      "BrowserHome": 0xb2,
      "NumpadDivide": 0xb5,
      "PrintScreen": 0xb7,
      "AltRight": 0xb8,
//      "NumLock": 0xc5,
      "Pause": 0xc6,
      "Home": 0xc7,
      "ArrowUp": 0xc8,
      "PageUp": 0xc9,
      "ArrowLeft": 0xcb,
      "ArrowRight": 0xcd,
      "End": 0xcf,
      "ArrowDown": 0xd0,
      "PageDown": 0xd1,
      "Insert": 0xd2,
      "Delete": 0xd3,
      "OSLeft": 0xdb,
      "OSRight": 0xdc,
      "ContextMenu": 0xdd,
      "Power": 0xde,
      "BrowserSearch": 0xe5,
      "BrowserFavorites": 0xe6,
      "BrowserRefresh": 0xe7,
      "BrowserStop": 0xe8,
      "BrowserForward": 0xe9,
      "BrowserBack": 0xea,
      "LaunchApp1": 0xeb,
      "LaunchMail": 0xec,
      "MediaSelect": 0xed,
      "Lang2": 0xf1,
      "Lang1": 0xf2
    };

    function getScancode(evt) {
      if (evt.code !== undefined && (evt.code in scancodeMap)) {
        return scancodeMap[evt.code];
      }
      return null;
    }

    return {
        getKeysym : getKeysym,
        getScancode : getScancode,
        toggleVirtualNumLock : function () {
          virtualNumLock = !virtualNumLock;
        },
    };
})();

// Takes a DOM keyboard event and:
// - determines which keysym it represents
// This information is collected into an object which is passed to the next() function. (one call per event)
function KeyEventDecoder(modifierState, next) {
    "use strict";
    var downkeys = {};

    function process(evt, down) {
        var result = {type: down ? "keydown" : "keyup"};

        // console.log("process: " + (down ? "down" : "up") + ", " +
        //             "key " + evt.key + ", " +
        //             "keyCode " + evt.keyCode + ", " +
        //             "keyIdentifier " + evt.keyIdentifier + ", " +
        //             "charCode " + evt.charCode + ", " +
        //             "location " + evt.location);

        // Virtual Num Lock on Mac
        if (down && ((evt.key == "Clear") || (evt.keyIdentifier == "Clear"))) {
          kbdUtil.toggleVirtualNumLock();
          return;
        }

        result.scancode = kbdUtil.getScancode(evt);
        // Even if we get the scancode directly from DOM-3, we still need
        // to get keysym which is what QEMU uses to sync NumLock and CapsLock.
        result.keysym = kbdUtil.getKeysym(evt);
        if (!result.scancode) {
          if (!result.keysym) {
            return;
          }
          result.scancode = scancode_mapper.lookup(result.keysym.keysym);
        } else if (!result.keysym) {
          // This should only happen if there is a bug with the getKeysym()
          // function or when browsers like FF decides to break backwards
          // compatibility, in which case, there is no reason to have
          // the rest of the code throw exceptions, so use a dummy keysym.
          result.keysym = keysyms.lookup(32);
        }

        // Keep track of which keys are down by scancode.
        if (down) {
          downkeys[result.scancode] = result.keysym;
        } else if (result.scancode in downkeys) {
          delete downkeys[result.scancode];
        }

        next(result);
    }

    function releaseAll() {
        var key;
        for (key in downkeys) {
          next({type: "keyup", scancode: key, keysym: downkeys[key]});
        }
    }

    return {
        keydown: function(evt) {
            // If key is a letter, and no modifier other than shift is
            // is pressed, defer processing until keypress so we can figure
            // out whether the letter we got is upper case or lower case.
            // QEMU uses the symbol for the purpose of doing its own CapsLock
            // syncing.
            if (!(evt.keyCode >= 65 && evt.keyCode <= 90) ||
                evt.ctrlKey || evt.altKey || evt.metaKey || evt.altGraphKey) {
              process(evt, true);
              return true;
            }
            return false;
        },
        keypress: function(evt) {
            process(evt, true);
            return true;
        },
        keyup: function(evt) {
            process(evt, false);
            return true;
        },
        syncModifiers: function(evt) {
        },
        releaseAll: releaseAll
    };
}
