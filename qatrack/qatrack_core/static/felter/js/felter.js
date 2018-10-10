/*!
 * Felter 0.0.1
 *
 */
(function (factory) {
    if (typeof define === 'function' && define.amd) {
        // AMD. Register as an anonymous module.
        define(['jquery'], factory);
    } else if (typeof exports === 'object') {
        // Node/CommonJS
        factory(require('jquery'));
    } else {
        // Browser globals
        factory(jQuery);
    }
}(function (jQuery) {
    // This is needed so we can catch the AMD loader configuration and use it
    // The inner file should be wrapped (by `banner.start.js`) in a function that
    // returns the AMD loader references.
    var FELT =
        (function () {
            // Restore the Select2 AMD loader so it can be used
            // Needed mostly in the language files, where the loader is not inserted
            if (jQuery && jQuery.fn && jQuery.fn.felter && jQuery.fn.felter.amd) {
                var FELT = jQuery.fn.felter.amd;
            }
            var FELT;
            (function () {
                if (!FELT || !FELT.requirejs) {
                    if (!FELT) {
                        FELT = {};
                    } else {
                        require = FELT;
                    }
                    var requirejs, require, define;
                    (function (undef) {
                        var main, req, makeMap, handlers,
                            defined = {},
                            waiting = {},
                            config = {},
                            defining = {},
                            hasOwn = Object.prototype.hasOwnProperty,
                            aps = [].slice,
                            jsSuffixRegExp = /\.js$/;

                        function hasProp(obj, prop) {
                            return hasOwn.call(obj, prop);
                        }

                        /**
                         * Given a relative module name, like ./something, normalize it to
                         * a real name that can be mapped to a path.
                         * @param {String} name the relative name
                         * @param {String} baseName a real name that the name arg is relative
                         * to.
                         * @returns {String} normalized name
                         */
                        function normalize(name, baseName) {
                            var nameParts, nameSegment, mapValue, foundMap, lastIndex,
                                foundI, foundStarMap, starI, i, j, part,
                                baseParts = baseName && baseName.split("/"),
                                map = config.map,
                                starMap = (map && map['*']) || {};

                            //Adjust any relative paths.
                            if (name && name.charAt(0) === ".") {
                                //If have a base name, try to normalize against it,
                                //otherwise, assume it is a top-level require that will
                                //be relative to baseUrl in the end.
                                if (baseName) {
                                    name = name.split('/');
                                    lastIndex = name.length - 1;

                                    // Node .js allowance:
                                    if (config.nodeIdCompat && jsSuffixRegExp.test(name[lastIndex])) {
                                        name[lastIndex] = name[lastIndex].replace(jsSuffixRegExp, '');
                                    }

                                    //Lop off the last part of baseParts, so that . matches the
                                    //"directory" and not name of the baseName's module. For instance,
                                    //baseName of "one/two/three", maps to "one/two/three.js", but we
                                    //want the directory, "one/two" for this normalization.
                                    name = baseParts.slice(0, baseParts.length - 1).concat(name);

                                    //start trimDots
                                    for (i = 0; i < name.length; i += 1) {
                                        part = name[i];
                                        if (part === ".") {
                                            name.splice(i, 1);
                                            i -= 1;
                                        } else if (part === "..") {
                                            if (i === 1 && (name[2] === '..' || name[0] === '..')) {
                                                //End of the line. Keep at least one non-dot
                                                //path segment at the front so it can be mapped
                                                //correctly to disk. Otherwise, there is likely
                                                //no path mapping for a path starting with '..'.
                                                //This can still fail, but catches the most reasonable
                                                //uses of ..
                                                break;
                                            } else if (i > 0) {
                                                name.splice(i - 1, 2);
                                                i -= 2;
                                            }
                                        }
                                    }
                                    //end trimDots

                                    name = name.join("/");
                                } else if (name.indexOf('./') === 0) {
                                    // No baseName, so this is ID is resolved relative
                                    // to baseUrl, pull off the leading dot.
                                    name = name.substring(2);
                                }
                            }

                            //Apply map config if available.
                            if ((baseParts || starMap) && map) {
                                nameParts = name.split('/');

                                for (i = nameParts.length; i > 0; i -= 1) {
                                    nameSegment = nameParts.slice(0, i).join("/");

                                    if (baseParts) {
                                        //Find the longest baseName segment match in the config.
                                        //So, do joins on the biggest to smallest lengths of baseParts.
                                        for (j = baseParts.length; j > 0; j -= 1) {
                                            mapValue = map[baseParts.slice(0, j).join('/')];

                                            //baseName segment has  config, find if it has one for
                                            //this name.
                                            if (mapValue) {
                                                mapValue = mapValue[nameSegment];
                                                if (mapValue) {
                                                    //Match, update name to the new value.
                                                    foundMap = mapValue;
                                                    foundI = i;
                                                    break;
                                                }
                                            }
                                        }
                                    }

                                    if (foundMap) {
                                        break;
                                    }

                                    //Check for a star map match, but just hold on to it,
                                    //if there is a shorter segment match later in a matching
                                    //config, then favor over this star map.
                                    if (!foundStarMap && starMap && starMap[nameSegment]) {
                                        foundStarMap = starMap[nameSegment];
                                        starI = i;
                                    }
                                }

                                if (!foundMap && foundStarMap) {
                                    foundMap = foundStarMap;
                                    foundI = starI;
                                }

                                if (foundMap) {
                                    nameParts.splice(0, foundI, foundMap);
                                    name = nameParts.join('/');
                                }
                            }

                            return name;
                        }

                        function makeRequire(relName, forceSync) {
                            return function () {
                                //A version of a require function that passes a moduleName
                                //value for items that may need to
                                //look up paths relative to the moduleName
                                var args = aps.call(arguments, 0);

                                //If first arg is not require('string'), and there is only
                                //one arg, it is the array form without a callback. Insert
                                //a null so that the following concat is correct.
                                if (typeof args[0] !== 'string' && args.length === 1) {
                                    args.push(null);
                                }
                                return req.apply(undef, args.concat([relName, forceSync]));
                            };
                        }

                        function makeNormalize(relName) {
                            return function (name) {
                                return normalize(name, relName);
                            };
                        }

                        function makeLoad(depName) {
                            return function (value) {
                                defined[depName] = value;
                            };
                        }

                        function callDep(name) {
                            if (hasProp(waiting, name)) {
                                var args = waiting[name];
                                delete waiting[name];
                                defining[name] = true;
                                main.apply(undef, args);
                            }

                            if (!hasProp(defined, name) && !hasProp(defining, name)) {
                                throw new Error('No ' + name);
                            }
                            return defined[name];
                        }

                        //Turns a plugin!resource to [plugin, resource]
                        //with the plugin being undefined if the name
                        //did not have a plugin prefix.
                        function splitPrefix(name) {
                            var prefix,
                                index = name ? name.indexOf('!') : -1;
                            if (index > -1) {
                                prefix = name.substring(0, index);
                                name = name.substring(index + 1, name.length);
                            }
                            return [prefix, name];
                        }

                        /**
                         * Makes a name map, normalizing the name, and using a plugin
                         * for normalization if necessary. Grabs a ref to plugin
                         * too, as an optimization.
                         */
                        makeMap = function (name, relName) {
                            var plugin,
                                parts = splitPrefix(name),
                                prefix = parts[0];

                            name = parts[1];

                            if (prefix) {
                                prefix = normalize(prefix, relName);
                                plugin = callDep(prefix);
                            }

                            //Normalize according
                            if (prefix) {
                                if (plugin && plugin.normalize) {
                                    name = plugin.normalize(name, makeNormalize(relName));
                                } else {
                                    name = normalize(name, relName);
                                }
                            } else {
                                name = normalize(name, relName);
                                parts = splitPrefix(name);
                                prefix = parts[0];
                                name = parts[1];
                                if (prefix) {
                                    plugin = callDep(prefix);
                                }
                            }

                            //Using ridiculous property names for space reasons
                            return {
                                f: prefix ? prefix + '!' + name : name, //fullName
                                n: name,
                                pr: prefix,
                                p: plugin
                            };
                        };

                        function makeConfig(name) {
                            return function () {
                                return (config && config.config && config.config[name]) || {};
                            };
                        }

                        handlers = {
                            require: function (name) {
                                return makeRequire(name);
                            },
                            exports: function (name) {
                                var e = defined[name];
                                if (typeof e !== 'undefined') {
                                    return e;
                                } else {
                                    return (defined[name] = {});
                                }
                            },
                            module: function (name) {
                                return {
                                    id: name,
                                    uri: '',
                                    exports: defined[name],
                                    config: makeConfig(name)
                                };
                            }
                        };

                        main = function (name, deps, callback, relName) {
                            var cjsModule, depName, ret, map, i,
                                args = [],
                                callbackType = typeof callback,
                                usingExports;

                            //Use name if no relName
                            relName = relName || name;

                            //Call the callback to define the module, if necessary.
                            if (callbackType === 'undefined' || callbackType === 'function') {
                                //Pull out the defined dependencies and pass the ordered
                                //values to the callback.
                                //Default to [require, exports, module] if no deps
                                deps = !deps.length && callback.length ? ['require', 'exports', 'module'] : deps;
                                for (i = 0; i < deps.length; i += 1) {
                                    map = makeMap(deps[i], relName);
                                    depName = map.f;

                                    //Fast path CommonJS standard dependencies.
                                    if (depName === "require") {
                                        args[i] = handlers.require(name);
                                    } else if (depName === "exports") {
                                        //CommonJS module spec 1.1
                                        args[i] = handlers.exports(name);
                                        usingExports = true;
                                    } else if (depName === "module") {
                                        //CommonJS module spec 1.1
                                        cjsModule = args[i] = handlers.module(name);
                                    } else if (hasProp(defined, depName) ||
                                        hasProp(waiting, depName) ||
                                        hasProp(defining, depName)) {
                                        args[i] = callDep(depName);
                                    } else if (map.p) {
                                        map.p.load(map.n, makeRequire(relName, true), makeLoad(depName), {});
                                        args[i] = defined[depName];
                                    } else {
                                        throw new Error(name + ' missing ' + depName);
                                    }
                                }

                                ret = callback ? callback.apply(defined[name], args) : undefined;

                                if (name) {
                                    //If setting exports via "module" is in play,
                                    //favor that over return value and exports. After that,
                                    //favor a non-undefined return value over exports use.
                                    if (cjsModule && cjsModule.exports !== undef &&
                                        cjsModule.exports !== defined[name]) {
                                        defined[name] = cjsModule.exports;
                                    } else if (ret !== undef || !usingExports) {
                                        //Use the return value from the function.
                                        defined[name] = ret;
                                    }
                                }
                            } else if (name) {
                                //May just be an object definition for the module. Only
                                //worry about defining if have a module name.
                                defined[name] = callback;
                            }
                        };

                        requirejs = require = req = function (deps, callback, relName, forceSync, alt) {
                            if (typeof deps === "string") {
                                if (handlers[deps]) {
                                    //callback in this case is really relName
                                    return handlers[deps](callback);
                                }
                                //Just return the module wanted. In this scenario, the
                                //deps arg is the module name, and second arg (if passed)
                                //is just the relName.
                                //Normalize module name, if it contains . or ..
                                return callDep(makeMap(deps, callback).f);
                            } else if (!deps.splice) {
                                //deps is a config object, not an array.
                                config = deps;
                                if (config.deps) {
                                    req(config.deps, config.callback);
                                }
                                if (!callback) {
                                    return;
                                }

                                if (callback.splice) {
                                    //callback is an array, which means it is a dependency list.
                                    //Adjust args if there are dependencies
                                    deps = callback;
                                    callback = relName;
                                    relName = null;
                                } else {
                                    deps = undef;
                                }
                            }

                            //Support require(['a'])
                            callback = callback || function () {
                                };

                            //If relName is a function, it is an errback handler,
                            //so remove it.
                            if (typeof relName === 'function') {
                                relName = forceSync;
                                forceSync = alt;
                            }

                            //Simulate async callback;
                            if (forceSync) {
                                main(undef, deps, callback, relName);
                            } else {
                                //Using a non-zero value because of concern for what old browsers
                                //do, and latest browsers "upgrade" to 4 if lower value is used:
                                //http://www.whatwg.org/specs/web-apps/current-work/multipage/timers.html#dom-windowtimers-settimeout:
                                //If want a value immediately, use require('id') instead -- something
                                //that works in almond on the global level, but not guaranteed and
                                //unlikely to work in other AMD implementations.
                                setTimeout(function () {
                                    main(undef, deps, callback, relName);
                                }, 4);
                            }

                            return req;
                        };

                        /**
                         * Just drops the config on the floor, but returns req in case
                         * the config return value is used.
                         */
                        req.config = function (cfg) {
                            return req(cfg);
                        };

                        /**
                         * Expose module registry for debugging and tooling
                         */
                        requirejs._defined = defined;

                        define = function (name, deps, callback) {
                            if (typeof name !== 'string') {
                                throw new Error('See almond README: incorrect module build, no module name');
                            }

                            //This module may not have dependencies
                            if (!deps.splice) {
                                //deps is not an array, so probably means
                                //an object literal or factory function for
                                //the value. Adjust args.
                                callback = deps;
                                deps = [];
                            }

                            if (!hasProp(defined, name) && !hasProp(waiting, name)) {
                                waiting[name] = [name, deps, callback];
                            }
                        };

                        define.amd = {
                            jQuery: true
                        };
                    }());

                    FELT.requirejs = requirejs;
                    FELT.require = require;
                    FELT.define = define;
                }
            }());
            FELT.define("almond", function () {
            });

            /* global jQuery:false, $:false */
            FELT.define('jquery', [], function () {
                var _$ = jQuery || $;

                if (_$ == null && console && console.error) {
                    console.error(
                        'Felter: An instance of jQuery or a jQuery-compatible library was not ' +
                        'found. Make sure that you are including jQuery before Felter on your ' +
                        'web page.'
                    );
                }

                return _$;
            });

            FELT.define('felter/utils', ['jquery'], function ($) {
                var Utils = {};

                function getMethods(theClass) {
                    var proto = theClass.prototype;

                    var methods = [];

                    for (var methodName in proto) {
                        var m = proto[methodName];

                        if (typeof m !== 'function') {
                            continue;
                        }

                        if (methodName === 'constructor') {
                            continue;
                        }

                        methods.push(methodName);
                    }

                    return methods;
                }

                Utils.Extend = function (ChildClass, SuperClass) {
                    var __hasProp = {}.hasOwnProperty;

                    function BaseConstructor() {
                        this.constructor = ChildClass;
                    }

                    for (var key in SuperClass) {
                        if (__hasProp.call(SuperClass, key)) {
                            ChildClass[key] = SuperClass[key];
                        }
                    }

                    BaseConstructor.prototype = SuperClass.prototype;
                    ChildClass.prototype = new BaseConstructor();
                    ChildClass.__super__ = SuperClass.prototype;

                    return ChildClass;
                };

                var Observable = function () {
                    this.listeners = {};
                };

                Observable.prototype.on = function (event, callback) {
                    this.listeners = this.listeners || {};

                    if (event in this.listeners) {
                        this.listeners[event].push(callback);
                    } else {
                        this.listeners[event] = [callback];
                    }
                };

                Observable.prototype.trigger = function (event) {
                    var slice = Array.prototype.slice;
                    var params = slice.call(arguments, 1);

                    this.listeners = this.listeners || {};

                    // Params should always come in as an array
                    if (params == null) {
                        params = [];
                    }

                    // If there are no arguments to the event, use a temporary object
                    if (params.length === 0) {
                        params.push({});
                    }

                    // Set the `_type` of the first object to the event
                    params[0]._type = event;

                    if (event in this.listeners) {
                        this.invoke(this.listeners[event], slice.call(arguments, 1));
                    }

                    if ('*' in this.listeners) {
                        this.invoke(this.listeners['*'], arguments);
                    }
                };

                Observable.prototype.invoke = function (listeners, params) {
                    for (var i = 0, len = listeners.length; i < len; i++) {
                        listeners[i].apply(this, params);
                    }
                };

                Utils.Observable = Observable;

                Utils.get_datas = function (felter, values, in_array) {
                    var datas = [];
                    $.each(felter.data, function (k, v) {
                        if (!in_array && $.inArray(parseInt(v.value), values) === -1) {
                            datas.push(v);
                        } else if (in_array && $.inArray(parseInt(v.value), values) !== -1) {
                            datas.push(v);
                        }
                    });

                    return datas;
                };

                return Utils;

            });

            FELT.define('felter/defaults', ['jquery', 'require', './utils'], function ($, require, Utils) {
                /*function Defaults() {
                    this.reset();
                }

                Defaults.prototype.apply = function (options) {
                    options = $.extend(true, {}, this.defaults, options);

                    if (options.dataAdapter == null) {
                        if (options.ajax != null) {
                            options.dataAdapter = AjaxData;
                        } else if (options.data != null) {
                            options.dataAdapter = ArrayData;
                        } else {
                            options.dataAdapter = SelectData;
                        }

                        if (options.minimumInputLength > 0) {
                            options.dataAdapter = Utils.Decorate(
                                options.dataAdapter,
                                MinimumInputLength
                            );
                        }

                        if (options.maximumInputLength > 0) {
                            options.dataAdapter = Utils.Decorate(
                                options.dataAdapter,
                                MaximumInputLength
                            );
                        }

                        if (options.maximumSelectionLength > 0) {
                            options.dataAdapter = Utils.Decorate(
                                options.dataAdapter,
                                MaximumSelectionLength
                            );
                        }

                        if (options.tags) {
                            options.dataAdapter = Utils.Decorate(options.dataAdapter, Tags);
                        }

                        if (options.tokenSeparators != null || options.tokenizer != null) {
                            options.dataAdapter = Utils.Decorate(
                                options.dataAdapter,
                                Tokenizer
                            );
                        }

                        if (options.query != null) {
                            var Query = require(options.amdBase + 'compat/query');

                            options.dataAdapter = Utils.Decorate(
                                options.dataAdapter,
                                Query
                            );
                        }

                        if (options.initSelection != null) {
                            var InitSelection = require(options.amdBase + 'compat/initSelection');

                            options.dataAdapter = Utils.Decorate(
                                options.dataAdapter,
                                InitSelection
                            );
                        }
                    }

                    if (options.resultsAdapter == null) {
                        options.resultsAdapter = ResultsList;

                        if (options.ajax != null) {
                            options.resultsAdapter = Utils.Decorate(
                                options.resultsAdapter,
                                InfiniteScroll
                            );
                        }

                        if (options.placeholder != null) {
                            options.resultsAdapter = Utils.Decorate(
                                options.resultsAdapter,
                                HidePlaceholder
                            );
                        }

                        if (options.selectOnClose) {
                            options.resultsAdapter = Utils.Decorate(
                                options.resultsAdapter,
                                SelectOnClose
                            );
                        }
                    }

                    if (options.dropdownAdapter == null) {
                        if (options.multiple) {
                            options.dropdownAdapter = Dropdown;
                        } else {
                            var SearchableDropdown = Utils.Decorate(Dropdown, DropdownSearch);

                            options.dropdownAdapter = SearchableDropdown;
                        }

                        if (options.minimumResultsForSearch !== 0) {
                            options.dropdownAdapter = Utils.Decorate(
                                options.dropdownAdapter,
                                MinimumResultsForSearch
                            );
                        }

                        if (options.closeOnSelect) {
                            options.dropdownAdapter = Utils.Decorate(
                                options.dropdownAdapter,
                                CloseOnSelect
                            );
                        }

                        if (
                            options.dropdownCssClass != null ||
                            options.dropdownCss != null ||
                            options.adaptDropdownCssClass != null
                        ) {
                            var DropdownCSS = require(options.amdBase + 'compat/dropdownCss');

                            options.dropdownAdapter = Utils.Decorate(
                                options.dropdownAdapter,
                                DropdownCSS
                            );
                        }

                        options.dropdownAdapter = Utils.Decorate(
                            options.dropdownAdapter,
                            AttachBody
                        );
                    }

                    if (options.selectionAdapter == null) {
                        if (options.multiple) {
                            options.selectionAdapter = MultipleSelection;
                        } else {
                            options.selectionAdapter = SingleSelection;
                        }

                        // Add the placeholder mixin if a placeholder was specified
                        if (options.placeholder != null) {
                            options.selectionAdapter = Utils.Decorate(
                                options.selectionAdapter,
                                Placeholder
                            );
                        }

                        if (options.allowClear) {
                            options.selectionAdapter = Utils.Decorate(
                                options.selectionAdapter,
                                AllowClear
                            );
                        }

                        if (options.multiple) {
                            options.selectionAdapter = Utils.Decorate(
                                options.selectionAdapter,
                                SelectionSearch
                            );
                        }

                        if (
                            options.containerCssClass != null ||
                            options.containerCss != null ||
                            options.adaptContainerCssClass != null
                        ) {
                            var ContainerCSS = require(options.amdBase + 'compat/containerCss');

                            options.selectionAdapter = Utils.Decorate(
                                options.selectionAdapter,
                                ContainerCSS
                            );
                        }

                        options.selectionAdapter = Utils.Decorate(
                            options.selectionAdapter,
                            EventRelay
                        );
                    }

                    if (typeof options.language === 'string') {
                        // Check if the language is specified with a region
                        if (options.language.indexOf('-') > 0) {
                            // Extract the region information if it is included
                            var languageParts = options.language.split('-');
                            var baseLanguage = languageParts[0];

                            options.language = [options.language, baseLanguage];
                        } else {
                            options.language = [options.language];
                        }
                    }

                    if ($.isArray(options.language)) {
                        var languages = new Translation();
                        options.language.push('en');

                        var languageNames = options.language;

                        for (var l = 0; l < languageNames.length; l++) {
                            var name = languageNames[l];
                            var language = {};

                            try {
                                // Try to load it with the original name
                                language = Translation.loadPath(name);
                            } catch (e) {
                                try {
                                    // If we couldn't load it, check if it wasn't the full path
                                    name = this.defaults.amdLanguageBase + name;
                                    language = Translation.loadPath(name);
                                } catch (ex) {
                                    // The translation could not be loaded at all. Sometimes this is
                                    // because of a configuration problem, other times this can be
                                    // because of how Select2 helps load all possible translation files.
                                    if (options.debug && window.console && console.warn) {
                                        console.warn(
                                            'Select2: The language file for "' + name + '" could not be ' +
                                            'automatically loaded. A fallback will be used instead.'
                                        );
                                    }

                                    continue;
                                }
                            }

                            languages.extend(language);
                        }

                        options.translations = languages;
                    } else {
                        var baseTranslation = Translation.loadPath(
                            this.defaults.amdLanguageBase + 'en'
                        );
                        var customTranslation = new Translation(options.language);

                        customTranslation.extend(baseTranslation);

                        options.translations = customTranslation;
                    }

                    return options;
                };

                Defaults.prototype.reset = function () {
                    /!*function stripDiacritics(text) {
                        // Used 'uni range + named function' from http://jsperf.com/diacritics/18
                        function match(a) {
                            return DIACRITICS[a] || a;
                        }

                        return text.replace(/[^\u0000-\u007E]/g, match);
                    }*!/

                    /!*function matcher(params, data) {
                        // Always return the object if there is nothing to compare
                        if ($.trim(params.term) === '') {
                            return data;
                        }

                        // Do a recursive check for options with children
                        if (data.children && data.children.length > 0) {
                            // Clone the data object if there are children
                            // This is required as we modify the object to remove any non-matches
                            var match = $.extend(true, {}, data);

                            // Check each child of the option
                            for (var c = data.children.length - 1; c >= 0; c--) {
                                var child = data.children[c];

                                var matches = matcher(params, child);

                                // If there wasn't a match, remove the object in the array
                                if (matches == null) {
                                    match.children.splice(c, 1);
                                }
                            }

                            // If any children matched, return the new object
                            if (match.children.length > 0) {
                                return match;
                            }

                            // If there were no matching children, check just the plain object
                            return matcher(params, match);
                        }

                        var original = stripDiacritics(data.text).toUpperCase();
                        var term = stripDiacritics(params.term).toUpperCase();

                        // Check if the text contains the term
                        if (original.indexOf(term) > -1) {
                            return data;
                        }

                        // If it doesn't contain the term, don't return anything
                        return null;
                    }*!/

                    this.defaults = {
                        amdBase: './',
                        amdLanguageBase: './i18n/',
                        closeOnSelect: true,
                        debug: false,
                        dropdownAutoWidth: false,
                        escapeMarkup: Utils.escapeMarkup,
                        language: EnglishTranslation,
                        matcher: matcher,
                        minimumInputLength: 0,
                        maximumInputLength: 0,
                        maximumSelectionLength: 0,
                        minimumResultsForSearch: 0,
                        selectOnClose: false,
                        sorter: function (data) {
                            return data;
                        },
                        templateResult: function (result) {
                            return result.text;
                        },
                        templateSelection: function (selection) {
                            return selection.text;
                        },
                        theme: 'default',
                        width: 'resolve'
                    };
                };

                /!*Defaults.prototype.set = function (key, value) {
                    var camelKey = $.camelCase(key);

                    var data = {};
                    data[camelKey] = value;

                    var convertedData = Utils._convertData(data);

                    $.extend(this.defaults, convertedData);
                };*!/

                var defaults = new Defaults();

                return defaults;*/
            });

            FELT.define('felter/core',['jquery', './utils'/*, './options', './keys'*/], function ($, Utils/*, Options, KEYS*/) {

                var Felter = function($element, options) {
                    if ($element.data('felter') != null) {
                        $element.data('felter').destroy();
                    }

                    var self = this;
                    self.$element = $element;

                    if (self.$element.prop('tagName') !== 'SELECT') {
                        throw new Error('Felter element must be a select');
                    }

                    self.id = self._generateId($element);

                    self.options = options || {};

                    Felter.__super__.constructor.call(self);

                    var $container = self.render();
                    self._placeContainer($container);

                    $element.data('felter', self);

                    // $.each(self.options.dependent_on_filters, function() {
                    //     if (this.element.data('felter')) {
                    //         this.element.data('felter').filters_dependent_on.push([self, this]);
                    //     } else {
                    //         if (this.element.data('felters_dependent')) {
                    //             this.element.data('felters_dependent').push([self, this]);
                    //         } else {
                    //             this.element.data('felters_dependent', [[self, this]]);
                    //         }
                    //     }
                    // });
                    // if (self.$element.data('felters_dependent')) {
                    //     $.each(self.$element.data('felters_dependent'), function(i, v) {
                    //         self.filters_dependent_on.push(v);
                    //     })
                    // }
                    // console.log(self.options.dependent_on_filters);

                    // $(self.$element).trigger('change');
                };

                Utils.Extend(Felter, Utils.Observable);

                Felter.prototype._generateId = function ($element) {
                    var id = '';

                    if ($element.attr('id') != null) {
                        id = $element.attr('id');
                    } else {
                        throw new Error('Felter element must have id');
                    }

                    id = id.replace(/(:|\.|\[|\]|,)/g, '');
                    id = 'felter-' + id;

                    return id;
                };

                Felter.prototype._placeContainer = function ($container) {
                    // $container.insertAfter(this.$element);
                    $container.css('left', '0');
                    var width = this.options.width || this.$element.width;

                    if (width != null) {
                        $container.css('width', width);
                    }
                };

                Felter.prototype.render = function () {

                    var self = this;

                    var $container = $(
                        '<div id="felter-' + self.$element.attr('id') + '" class="felter felter-container ' + (self.options.mainDivClass || '') + '"></div>'
                    );

                    $container.attr('dir', self.options.dir);

                    $container.append('<div class="title-container"><label for="' + self.$element.attr('id') + '">' + (self.options.label || self.$element.attr('id')) + '</label></div>');
                    var $title_container = $container.find('.title-container');

                    var show_options_box = self.options.selectAll || self.options.selectNone || (self.options.filters && self.options.filters.length > 0);
                    $container.append('<div class="top-option-container ' + (show_options_box ? '' : ' hide') + '"></div>');
                    var $top_opt_container = $container.find('.top-option-container');

                    $container.append('<div class="option-container"></div>');
                    var $opt_container = $container.find('.option-container');

                    this.$container = $container;
                    self.$element.hide();

                    this.$container.addClass('felter-container');

                    if (self.options.selectAll) {
                        var $btn_select_all = $('<div class="select-all-container"><div class="felter-selectall ' + self.options.selectAllClass + '">All</div></div>');
                        $btn_select_all.click(function() {
                            self.selectAll();
                        });
                        $top_opt_container.append($btn_select_all);
                    }
                    if (self.options.selectNone) {
                        var $btn_select_none = $('<div class="select-all-container"><div class="felter-selectnone ' + self.options.selectAllClass + '">None</div></div>');
                        $btn_select_none.click(function() {
                            self.selectNone();
                        });
                        $top_opt_container.append($btn_select_none);
                    }
                    if (self.options.filters) {
                        $.each(self.options.filters, function(k, v) {
                            var $top_custom_div = $('<div class="' + (this.selected ? 'felter-selected' : '') + ' felter-top-option">' + this.label + '</div>');
                            var filt = this;
                            filt.$div = $top_custom_div;
                            $top_custom_div.click(function(e) {
                                filt.selected = !filt.selected;

                                self.updateCustomFilter(filt);
                            });
                            $top_opt_container.append($top_custom_div);
                        });
                    }

                    $container.css('left', '100px');
                    $container.insertAfter(self.$element);
                    if (self.options.height) {
                        $container.css('height', self.options.height + 'px');
                        if (self.options.slimscroll) {
                            $opt_container.slimscroll({
                                height: $container.height() - $top_opt_container.outerHeight(false) - $title_container.outerHeight(false),
                                wheelStep: 7
                            })
                        } else {
                            $opt_container.css('height', ($container.height() - $top_opt_container.outerHeight(false) - $title_container.outerHeight(false)) + 'px');
                        }
                    }

                    $container.data('element', self.$element);
                    self.$opts = self.$element.children('option');
                    self.data = [];
                    $.each(self.$opts, function() {

                        var orig_opt = this;
                        var selected = $(this).attr('selected') === 'selected';

                        var opt_data = {
                            value: this.value,
                            text: this.textContent,
                            felter: self,
                            $option: orig_opt,
                            $opt_container: $opt_container,
                            displayed: true,
                            filtered_self: false,
                            filtered_other: false,
                            selected: selected
                        };

                        // adds $div to opt_data
                        self.renderOption(opt_data);

                        self.data.push(opt_data);
                        opt_data.$div[0].opt_data = opt_data;
                    });

                    self.$element.change(function() {
                        var vals = self.$element.val();
                        self.selectOptionsByVal(vals);
                    });

                    var refresh_self_filters = false;
                    $.each(self.options.filters, function() {
                        if (this.refresh_on_dependent_changes) {
                            refresh_self_filters = true;
                        }
                    });

                    $.each(self.options.dependent_on_filters, function() {

                        self.elementChange(this);

                        var other_element = this.element;
                        // var filter = this.filter;
                        // if (this.is_ajax) {
                        //     other_element.change(function () {
                        //         filter(function (good_vals) {
                        //             var obj_datas_hide = Utils.get_datas(self, good_vals, false);
                        //             var obj_datas_show = Utils.get_datas(self, good_vals, true);
                        //
                        //             $.each(obj_datas_hide, function() {
                        //                 this.filtered_other = true;
                        //             });
                        //             $.each(obj_datas_show, function() {
                        //                 this.filtered_other = false;
                        //             });
                        //             self.updateView();
                        //         })
                        //     });
                        //
                        //
                        // } else {
                        //     other_element.change(function () {
                        //         var good_vals = filter();
                        //         var obj_datas_hide = Utils.get_datas(self, good_vals, false);
                        //         var obj_datas_show = Utils.get_datas(self, good_vals, true);
                        //
                        //         $.each(obj_datas_hide, function() {
                        //             this.filtered_other = true;
                        //         });
                        //         $.each(obj_datas_show, function() {
                        //             this.filtered_other = false;
                        //         });
                        //         self.updateView();
                        //     });
                        // }

                        if (refresh_self_filters) {
                            other_element.change(function() {
                                $.each(self.data, function() {
                                    self.updateSelfFilters(this);
                                })
                            })
                        }

                    });
                    if (self.options.initially_displayed) {
                        self.updateView();
                    }
                    return $container;
                };

                Felter.prototype.elementChange = function(filt) {
                    var self = this;
                    var other_element = filt.element;
                    var filter = filt.filter;
                    if (filt.is_ajax) {
                        other_element.change(function () {
                            filter(function (good_vals) {
                                var obj_datas_hide = Utils.get_datas(self, good_vals, false);
                                var obj_datas_show = Utils.get_datas(self, good_vals, true);

                                $.each(obj_datas_hide, function() {
                                    this.filtered_other = true;
                                });
                                $.each(obj_datas_show, function() {
                                    this.filtered_other = false;
                                });
                                self.updateView();
                            })
                        });


                    } else {
                        other_element.change(function () {
                            var good_vals = filter();
                            var obj_datas_hide = Utils.get_datas(self, good_vals, false);
                            var obj_datas_show = Utils.get_datas(self, good_vals, true);

                            $.each(obj_datas_hide, function() {
                                this.filtered_other = true;
                            });
                            $.each(obj_datas_show, function() {
                                this.filtered_other = false;
                            });
                            self.updateView();
                        });
                    }

                };

                Felter.prototype.renderOption = function(opt_data) {
                    var self = this;
                    var selected = opt_data.selected;
                    var div_id = 'felter-option-div-' + opt_data.value;
                    var $div;

                    if (self.options.renderOption) {
                        $div = self.options.renderOption(opt_data);
                    } else {
                        $div = $('<div id="' + div_id + '" class="felter-option' + (selected ? ' felter-selected' : '') + '" title="' + $(opt_data.$option).attr('title') + '">'  + opt_data.text + '</div>');
                    }
                    if (!self.options.initially_displayed) {
                        opt_data.displayed = false;
                        $div.css('display', 'none');
                    }
                    opt_data.$div = $div;

                    $div.click(function(e) {

                        if (e.shiftKey && self.previously_selected) {

                            var $this = $(this);
                            var $prev = $(self.previously_selected);
                            var this_div_idx = $this.index();
                            var prev_sel_idx = $prev.index();
                            var $select_divs;

                            if (this_div_idx < prev_sel_idx) {
                                $select_divs = $this.nextUntil($prev);
                            } else {
                                $select_divs = $prev.nextUntil($this);
                            }

                            if ($prev[0].opt_data.selected) {
                                $.each($select_divs, function (i, v) {
                                    if (v.opt_data.displayed) {
                                        self.selectOption(v.opt_data, false);
                                    }
                                });
                                self.selectOption(opt_data, true);
                            } else {
                                $.each($select_divs, function (i, v) {
                                    self.deselectOption(v.opt_data, false);
                                });
                                self.deselectOption(opt_data, true);
                            }

                        } else {
                            if (!opt_data.selected) {
                                self.selectOption(opt_data, true);
                                self.previously_selected = this;
                            } else {
                                self.deselectOption(opt_data, true);
                                self.previously_selected = this;
                            }
                        }
                    });

                    opt_data.$opt_container.append($div);
                    self.updateSelfFilters(opt_data);
                };

                Felter.prototype.updateSelfFilters = function(opt_data) {
                    var self = this;
                    opt_data.filtered_self = self.shouldFilterFromSelf(opt_data);
                };

                Felter.prototype.updateCustomFilter = function(filt) {
                    var self = this;
                    if (filt.selected) {
                        filt.$div.addClass('felter-selected');
                    } else {
                        filt.$div.removeClass('felter-selected');
                    }
                    $.each(self.data, function() {
                        this.filtered_self = self.shouldFilterFromSelf(this);
                    });
                    self.updateView();
                };

                Felter.prototype.updateView = function() {
                    var self = this;
                    var changed = false;
                    $.each(self.data, function() {
                        if (!this.filtered_other && !this.filtered_self && !this.displayed) {
                            self.showOption(this);
                        } else if ((this.filtered_other || this.filtered_self) && this.displayed) {
                            var opt_changed = self.hideOption(this);
                            changed = opt_changed ? opt_changed : changed;
                        }
                    });
                    if (changed) {
                        self.$element.change();
                    }
                };

                Felter.prototype.shouldFilterFromSelf = function(obj_data) {
                    var self = this;
                    var should = false;
                    $.each(self.options.filters, function(k, v) {
                        var filter_data = this;
                        if ((filter_data.selected && filter_data.run_filter_when_selected) || (!filter_data.selected && !filter_data.run_filter_when_selected)) {
                            if (!filter_data.filter(obj_data)) {
                                should = true;
                            }
                        }
                    });
                    return should;
                };

                Felter.prototype.selectOption = function(opt_data, loop) {
                    if (!opt_data.selected) {
                        opt_data.$div.addClass('felter-selected');
                        $(opt_data.$option).prop('selected', true);
                        opt_data.selected = true;
                        if (loop) {
                            $(opt_data.$option).trigger('change')
                        }
                    }
                };

                Felter.prototype.deselectOption = function(opt_data, loop) {
                    if (opt_data.selected) {
                        opt_data.$div.removeClass('felter-selected');
                        $(opt_data.$option).prop('selected', false);
                        opt_data.selected = false;
                        if (loop) {
                            $(opt_data.$option).trigger('change')
                        }
                        return true;
                    }
                    return false;
                };

                Felter.prototype.selectOptionsByVal = function(values) {

                    var self = this;

                    if (!$.isArray(values)) {
                        return
                    }
                    $.each(self.data, function() {
                        if ($.inArray(this.value, values) > -1) {
                            self.showOption(this);
                            self.selectOption(this, false);
                        } else {
                            self.deselectOption(this, false);
                        }
                    });
                };

                Felter.prototype.hideOption = function(opt_data, loop) {
                    var changed = this.deselectOption(opt_data, loop);
                    opt_data.displayed = false;
                    $(opt_data.$div).slideUp('fast');
                    return changed;
                };

                Felter.prototype.showOption = function(opt_data) {
                    opt_data.displayed = true;
                    opt_data.$div.slideDown('fast');
                };

                Felter.prototype.selectAll = function() {
                    var self = this;
                    $.each(self.data, function() {
                        if (this.displayed) {
                            self.selectOption(this, false);
                        }
                    });
                    self.$element.trigger('change');
                };

                Felter.prototype.selectNone = function() {
                    var self = this;
                    $.each(self.data, function() {
                        self.deselectOption(this, false);
                    });
                    self.$element.trigger('change');
                };

                Felter.prototype.isFiltered = function(filter_name) {
                    var self = this;
                    return self.options.filters[filter_name].selected;
                };

                Felter.prototype.setFilter = function(filter_name, bool) {
                    var self = this;
                    var filt = self.options.filters[filter_name];
                    filt.selected = bool;
                    self.updateCustomFilter(filt);
                };

                Felter.prototype.val = function(value) {
                    return this.$element.val(value);
                };

                Felter.prototype._bindAdapters = function () {
                    this.dataAdapter.bind(this, this.$container);
                    this.selection.bind(this, this.$container);

                    this.dropdown.bind(this, this.$container);
                    this.results.bind(this, this.$container);
                };

                return Felter;

            });

            FELT.define('jquery-mousewheel', ['jquery'], function ($) {
                // Used to shim jQuery.mousewheel for non-full builds.
                return $;
            });

            FELT.define('jquery.felter', ['jquery', 'jquery-mousewheel', './felter/core', './felter/defaults'], function ($, _, Felter, Defaults) {
                if ($.fn.felter == null) {
                    // All methods that should return the element
                    var thisMethods = ['open', 'close', 'destroy'];

                    $.fn.felter = function (options) {
                        options = options || {};

                        if (typeof options === 'object') {
                            this.each(function () {
                                var instanceOptions = $.extend(true, {}, options);

                                var instance = new Felter($(this), instanceOptions);
                            });

                            return this;
                        } else if (typeof options === 'string') {
                            var ret;
                            var args = Array.prototype.slice.call(arguments, 1);

                            this.each(function () {
                                var instance = $(this).data('felter');

                                if (instance == null && window.console && console.error) {
                                    console.error(
                                        'The felter(\'' + options + '\') method was called on an ' +
                                        'element that is not using Select2.'
                                    );
                                }

                                ret = instance[options].apply(instance, args);
                            });

                            // Check if we should be returning `this`
                            if ($.inArray(options, thisMethods) > -1) {
                                return this;
                            }

                            return ret;
                        } else {
                            throw new Error('Invalid arguments for Felter: ' + options);
                        }
                    };
                }

                if ($.fn.felter.defaults == null) {
                    $.fn.felter.defaults = Defaults;
                }

                return Felter;
            });


            return {
                define: FELT.define,
                require: FELT.require
            };
        }());
    // Autoload the jQuery bindings
    // We know that all of the modules exist above this, so we're safe
    var felter = FELT.require('jquery.felter');

    // Hold the AMD module references on the jQuery function that was just loaded
    // This allows Felter to use the internal loader outside of this file, such
    // as in the language files.
    jQuery.fn.felter.amd = FELT;

    // Return the Felter instance for anyone who is importing it.
    return felter;
}));