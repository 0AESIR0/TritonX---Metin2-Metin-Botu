/* global React, ReactDOM */

const THEMES = {
  default: {
    id: 'default',
    name: 'Varsayılan',
    desc: 'Klasik kırmızı tema',
    color: 'red',
    logo: './assets/TritonXlogo.png',
    textLogo: './assets/TritonXTextLogo.png'
  },
  amethyst: {
    id: 'amethyst',
    name: 'Amethyst',
    desc: 'Ametist moru tema',
    color: 'purple',
    logo: './assets/TritonXlogoPurple.png',
    textLogo: './assets/TritonXTextLogoPurple.png'
  },
  voidnox: {
    id: 'voidnox',
    name: 'VoidNox',
    desc: 'Neon mavi tema',
    color: 'blue',
    logo: './assets/TritonXlogoBlue.png',
    textLogo: './assets/TritonXTextLogoBlue.png'
  },
  sylva: {
    id: 'sylva',
    name: 'VoltreSylva',
    desc: 'Doğa yeşili tema',
    color: 'green',
    logo: './assets/TritonXlogoGreen.png',
    textLogo: './assets/TritonXTextLogoGreen.png'
  },
  pulsarspark: {
    id: 'pulsarspark',
    name: 'PulsarSpark',
    desc: 'Elektrik sarısı tema',
    color: 'yellow',
    logo: './assets/TritonXlogoYellow.png',
    textLogo: './assets/TritonXTextLogoYellow.png'
  }
};

function applyTheme(themeId) {
  if (themeId === 'voidnox' || themeId === 'sylva' || themeId === 'pulsarspark' || themeId === 'amethyst') {
    document.documentElement.setAttribute('data-theme', themeId);
  } else {
    document.documentElement.removeAttribute('data-theme');
  }
}

function useInterval(callback, delay) {
  const savedCallback = React.useRef(callback);
  React.useEffect(() => {
    savedCallback.current = callback;
  }, [callback]);

  React.useEffect(() => {
    if (delay === null) return;
    const id = setInterval(() => savedCallback.current(), delay);
    return () => clearInterval(id);
  }, [delay]);
}

function App() {
  const [api, setApi] = React.useState(null);
  const [ready, setReady] = React.useState(false);
  const [state, setState] = React.useState(null);
  const [windows, setWindows] = React.useState([]);
  const [monitors, setMonitors] = React.useState([]);
  const [log, setLog] = React.useState([]);
  const [logCursor, setLogCursor] = React.useState(0);
  const logRef = React.useRef(null);
  const [presets, setPresets] = React.useState([]);
  const [presetName, setPresetName] = React.useState('');
  const [theme, setTheme] = React.useState('default');
  const [showSettings, setShowSettings] = React.useState(false);
  const [pendingTheme, setPendingTheme] = React.useState(null);

  React.useEffect(() => {
    applyTheme(theme);
  }, [theme]);
  
  const loadThemeFromBackend = React.useCallback(async () => {
    if (!api) return;
    try {
      const savedTheme = await api.get_theme();
      if (savedTheme && THEMES[savedTheme]) {
        setTheme(savedTheme);
        applyTheme(savedTheme);
      }
    } catch (e) {}
  }, [api]);

  React.useEffect(() => {
    if (api) {
      loadThemeFromBackend();
    }
  }, [api, loadThemeFromBackend]);
  React.useEffect(() => {
    const attach = () => {
      if (window.pywebview && window.pywebview.api) {
        setApi(window.pywebview.api);
      }
    };

    const onReady = () => attach();
    window.addEventListener('pywebviewready', onReady);
    attach();

    return () => window.removeEventListener('pywebviewready', onReady);
  }, []);

  const refreshPresets = React.useCallback(async () => {
    if (!api) return;
    try {
      const list = await api.list_presets();
      if (Array.isArray(list)) {
        setPresets(list);
      }
    } catch (e) {}
  }, [api]);

  const refresh = React.useCallback(async () => {
    if (!api) return;
    try {
      const [s, w, m] = await Promise.all([
        api.get_state(),
        api.list_windows(),
        api.list_monitors(),
      ]);
      setState(s);
      setWindows(w);
      setMonitors(m);
      setReady(true);
      refreshPresets();
    } catch (e) {
      setReady(false);
    }
  }, [api, refreshPresets]);

  const pullLogs = React.useCallback(async () => {
    if (!api) return;
    try {
      const res = await api.get_logs_since(logCursor);
      if (res && Array.isArray(res.items) && res.items.length) {
        setLog((prev) => {
          const merged = prev.concat(res.items);
          return merged.slice(-400);
        });
        setLogCursor((prev) => res.next_cursor || prev);
      }
    } catch (e) {}
  }, [api, logCursor]);

  React.useEffect(() => {
    const t = setTimeout(() => refresh(), 150);
    return () => clearTimeout(t);
  }, [refresh]);

  useInterval(() => {
    refresh();
    pullLogs();
  }, 600);

  React.useEffect(() => {
    const el = logRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [log]);

  const setField = async (key, value) => {
    if (!api) return;
    await api.set_config({ [key]: value });
    await refresh();
  };

  const start = async () => {
    if (!api) return;
    await api.start_bot();
    await refresh();
  };

  const stop = async () => {
    if (!api) return;
    await api.stop_bot();
    await refresh();
  };

  const onBrowseTemplates = async () => {
    if (!api) return;
    const picked = await api.pick_template_folder();
    if (picked) {
      await api.set_config({ template_folder: picked });
      await refresh();
    }
  };

  const onReloadTemplates = async () => {
    if (!api) return;
    await api.reload_templates();
    await refresh();
  };

  const onRefreshWindows = async () => {
    if (!api) return;
    const w = await api.list_windows();
    setWindows(w);
  };

  const onSavePreset = async () => {
    if (!api || !presetName.trim()) return;
    await api.save_preset(presetName.trim());
    setPresetName('');
    await refreshPresets();
  };

  const onLoadPreset = async (name) => {
    if (!api) return;
    await api.load_preset(name);
    await refresh();
  };

  const onDeletePreset = async (name) => {
    if (!api) return;
    await api.delete_preset(name);
    await refreshPresets();
  };

  const openSettings = () => {
    setPendingTheme(theme);
    setShowSettings(true);
  };

  const closeSettings = () => {
    setShowSettings(false);
    setPendingTheme(null);
  };

  const saveTheme = async () => {
    if (pendingTheme && api) {
      await api.set_theme(pendingTheme);
      setTheme(pendingTheme);
      applyTheme(pendingTheme);
    }
    setShowSettings(false);
  };

  const currentTheme = THEMES[theme] || THEMES.default;
  const running = state && state.running;

  return React.createElement(
    'div',
    { className: 'shell' },
    
    showSettings && React.createElement(
      'div',
      { className: 'modal-overlay', onClick: closeSettings },
      React.createElement(
        'div',
        { className: 'modal', onClick: (e) => e.stopPropagation() },
        React.createElement(
          'div',
          { className: 'modal-header' },
          React.createElement('div', { className: 'modal-title' }, '⚙️ Ayarlar'),
          React.createElement('button', { className: 'modal-close', onClick: closeSettings }, '✕')
        ),
        React.createElement(
          'div',
          { className: 'modal-body' },
          React.createElement('div', { className: 'theme-options' },
            Object.values(THEMES).map((t) =>
              React.createElement(
                'div',
                {
                  key: t.id,
                  className: 'theme-option' + (pendingTheme === t.id ? ' selected' : ''),
                  onClick: () => setPendingTheme(t.id)
                },
                React.createElement('div', { className: 'theme-preview ' + t.color }),
                React.createElement('div', { className: 'theme-info' },
                  React.createElement('div', { className: 'theme-name' }, t.name),
                  React.createElement('div', { className: 'theme-desc' }, t.desc)
                ),
                React.createElement('div', { className: 'theme-check' }, pendingTheme === t.id ? '✓' : '')
              )
            )
          )
        ),
        React.createElement(
          'div',
          { className: 'modal-footer' },
          React.createElement('button', { className: 'btn', onClick: closeSettings }, 'İptal'),
          React.createElement('button', { className: 'btn primary', onClick: saveTheme }, '💾 Kaydet')
        )
      )
    ),

    React.createElement(
      'div',
      { className: 'topbar' },
      React.createElement(
        'div',
        { className: 'topbar-inner' },
        React.createElement(
          'div',
          { className: 'brand-left' },
          React.createElement('div', { className: 'logo' },
            React.createElement('img', { src: currentTheme.logo, alt: 'TritonX' })
          ),
          React.createElement('div', { className: 'brand-title' }, 'TritonX')
        ),
        React.createElement(
          'div',
          { className: 'brand-center' },
          React.createElement('img', { className: 'text-logo', src: currentTheme.textLogo, alt: 'TritonX' })
        ),
        React.createElement(
          'div',
          { className: 'pill' },
          React.createElement(
            'div',
            { className: 'badge' },
            React.createElement('div', { className: 'dot ' + (running ? 'on' : '') }),
            running ? 'ÇALIŞIYOR' : 'BEKLEMEDE'
          ),
          React.createElement(
            'div',
            { className: 'badge' },
            'Hotkey: Z+C başlat, Z+V durdur'
          ),
          React.createElement(
            'button',
            { className: 'settings-btn', onClick: openSettings, title: 'Ayarlar' },
            '⚙️'
          )
        )
      )
    ),
    React.createElement(
      'div',
      { className: 'main' },
      React.createElement(
        'div',
        { className: 'card' },
        React.createElement(
          'div',
          { className: 'card-h' },
          React.createElement('h3', null, 'Kontrol')
        ),
        React.createElement(
          'div',
          { className: 'card-b' },
          React.createElement(
            'div',
            { className: 'actions', style: { marginBottom: 12 } },
            React.createElement(
              'button',
              { className: 'btn primary', onClick: start, disabled: !ready || running },
              'BOT BAŞLAT'
            ),
            React.createElement(
              'button',
              { className: 'btn danger', onClick: stop, disabled: !ready || !running },
              'DURDUR'
            )
          ),

          React.createElement('div', { className: 'row' },
            React.createElement('div', { className: 'label' }, 'Mod'),
            React.createElement(
              'select',
              {
                value: (state && state.mode) || 'window',
                onChange: (e) => setField('mode', e.target.value),
              },
              React.createElement('option', { value: 'window' }, 'Uygulama (Pencere)'),
              React.createElement('option', { value: 'screen' }, 'Ekran')
            )
          ),

          React.createElement('div', { className: 'row' },
            React.createElement('div', { className: 'label' }, 'Algılama'),
            React.createElement(
              'select',
              {
                value: (state && state.detection_mode) || 'template',
                onChange: (e) => setField('detection_mode', e.target.value),
              },
              React.createElement('option', { value: 'template' }, 'Template'),
              React.createElement('option', { value: 'color' }, 'Renk'),
              React.createElement('option', { value: 'metin_preset' }, 'Metine Göre')
            )
          ),

          React.createElement('div', { className: 'row' },
            React.createElement('div', { className: 'label' }, 'Input'),
            React.createElement(
              'select',
              {
                value: (state && state.input_method) || 'sendinput',
                onChange: (e) => setField('input_method', e.target.value),
              },
              React.createElement('option', { value: 'sendinput' }, 'SendInput (Windows API)'),
              React.createElement('option', { value: 'postmessage' }, 'PostMessage (Pencere)'),
              React.createElement('option', { value: 'pyautogui' }, 'PyAutoGUI')
            )
          ),

          (state && state.detection_mode) === 'template'
            ? React.createElement(
                React.Fragment,
                null,
                React.createElement('div', { className: 'row' },
                  React.createElement('div', { className: 'label' }, 'Template klasörü'),
                  React.createElement(
                    'div',
                    null,
                    React.createElement('input', {
                      className: 'input',
                      value: (state && state.template_folder) || '',
                      onChange: (e) => setField('template_folder', e.target.value),
                      placeholder: 'templates/',
                    }),
                    React.createElement('div', { className: 'actions', style: { marginTop: 10 } },
                      React.createElement('button', { className: 'btn', onClick: onBrowseTemplates }, 'Klasör Seç'),
                      React.createElement('button', { className: 'btn', onClick: onReloadTemplates }, 'Yükle')
                    ),
                    React.createElement('div', { className: 'small', style: { marginTop: 8 } },
                      'Yüklü template: ', String((state && state.template_count) || 0)
                    )
                  )
                )
              )
            : (state && state.detection_mode) === 'metin_preset'
              ? React.createElement(
                  React.Fragment,
                  null,
                  React.createElement('div', { className: 'row' },
                    React.createElement('div', { className: 'label' }, 'Metin Seçimi'),
                    React.createElement(
                      'select',
                      {
                        className: 'input',
                        value: (state && state.metin_preset) || 'golge',
                        onChange: (e) => setField('metin_preset', e.target.value),
                      },
                      React.createElement('option', { value: 'golge' }, 'Gölge Metini')
                    )
                  ),
                  React.createElement('div', { className: 'row' },
                    React.createElement('div', { className: 'label' }, 'Tolerans'),
                    React.createElement('input', {
                      className: 'input',
                      type: 'number',
                      min: 0,
                      max: 80,
                      value: (state && state.color_tolerance) || 20,
                      onChange: (e) => setField('color_tolerance', Number(e.target.value || 0)),
                    })
                  )
                )
              : React.createElement(
                  React.Fragment,
                  null,
                  React.createElement('div', { className: 'row' },
                    React.createElement('div', { className: 'label' }, 'Renk (HEX)'),
                    React.createElement('input', {
                      className: 'input',
                      value: (state && state.color_hex) || '#ffffff',
                      onChange: (e) => setField('color_hex', e.target.value),
                      placeholder: '#ff0000',
                    })
                  ),
                  React.createElement('div', { className: 'row' },
                    React.createElement('div', { className: 'label' }, 'Tolerans'),
                    React.createElement('input', {
                      className: 'input',
                      type: 'number',
                      min: 0,
                      max: 80,
                      value: (state && state.color_tolerance) || 20,
                      onChange: (e) => setField('color_tolerance', Number(e.target.value || 0)),
                    })
                  )
                ),

          (state && state.mode) === 'window'
            ? React.createElement(
                React.Fragment,
                null,
                React.createElement('div', { className: 'row' },
                  React.createElement('div', { className: 'label' }, 'Oyun penceresi'),
                  React.createElement(
                    'div',
                    null,
                    React.createElement(
                      'select',
                      {
                        value: (state && state.window_title) || '',
                        onChange: (e) => setField('window_title', e.target.value),
                      },
                      React.createElement('option', { value: '' }, 'Seç...'),
                      windows.map((w) => React.createElement('option', { key: w, value: w }, w))
                    ),
                    React.createElement('div', { className: 'actions', style: { marginTop: 10 } },
                      React.createElement('button', { className: 'btn', onClick: onRefreshWindows }, 'Yenile')
                    )
                  )
                )
              )
            : React.createElement(
                React.Fragment,
                null,
                React.createElement('div', { className: 'row' },
                  React.createElement('div', { className: 'label' }, 'Ekran'),
                  React.createElement(
                    'select',
                    {
                      value: String((state && state.monitor_index) || 1),
                      onChange: (e) => setField('monitor_index', Number(e.target.value || 1)),
                    },
                    monitors.map((m) => React.createElement('option', { key: m, value: m }, 'Ekran ' + m))
                  )
                )
              ),

          React.createElement('div', { className: 'row' },
            React.createElement('div', { className: 'label' }, 'Eşik'),
            React.createElement('input', {
              className: 'input',
              type: 'number',
              step: '0.01',
              min: '0.50',
              max: '0.95',
              value: (state && state.threshold) || 0.8,
              onChange: (e) => setField('threshold', Number(e.target.value || 0.8)),
            })
          ),

          React.createElement('div', { className: 'row' },
            React.createElement('div', { className: 'label' }, 'Tarama (dk)'),
            React.createElement('input', {
              className: 'input',
              type: 'number',
              step: '0.05',
              min: '0.1',
              max: '3.0',
              value: (state && state.scan_minutes) || 0.5,
              onChange: (e) => setField('scan_minutes', Number(e.target.value || 0.5)),
            })
          ),

          React.createElement('div', { className: 'row' },
            React.createElement('div', { className: 'label' }, 'Tıklama (dk)'),
            React.createElement('input', {
              className: 'input',
              type: 'number',
              step: '0.05',
              min: '0.1',
              max: '3.0',
              value: (state && state.click_minutes) || 0.5,
              onChange: (e) => setField('click_minutes', Number(e.target.value || 0.5)),
            })
          ),

          React.createElement('div', { className: 'row' },
            React.createElement('div', { className: 'label' }, 'Kamera bekleme (sn)'),
            React.createElement('input', {
              className: 'input',
              type: 'number',
              step: '0.1',
              min: '0.0',
              max: '2.0',
              value: (state && state.camera_seconds) || 0.0,
              onChange: (e) => setField('camera_seconds', Number(e.target.value || 0.0)),
            })
          ),

          React.createElement('div', { className: 'row' },
            React.createElement('div', { className: 'label' }, 'Oto toplama'),
            React.createElement(
              'select',
              {
                value: (state && state.auto_loot_mode) || 'passive',
                onChange: (e) => setField('auto_loot_mode', e.target.value),
              },
              React.createElement('option', { value: 'passive' }, 'Pasif'),
              React.createElement('option', { value: 'active' }, 'Aktif')
            )
          ),

          React.createElement('div', { className: 'row' },
            React.createElement('div', { className: 'label' }, 'Toplama aralığı (dk)'),
            React.createElement('input', {
              className: 'input',
              type: 'number',
              step: '0.01',
              min: '0.01',
              max: '0.50',
              value: (state && state.auto_loot_minutes) || 0.10,
              onChange: (e) => setField('auto_loot_minutes', Number(e.target.value || 0.10)),
              disabled: (state && state.auto_loot_mode) !== 'active',
            })
          ),

          React.createElement('div', { className: 'divider' }),

          React.createElement('div', { className: 'row' },
            React.createElement('div', { className: 'label' }, 'Bot Kontrol'),
            React.createElement(
              'select',
              {
                value: (state && state.captcha_enabled) ? 'active' : 'passive',
                onChange: (e) => setField('captcha_enabled', e.target.value === 'active'),
              },
              React.createElement('option', { value: 'passive' }, 'Pasif'),
              React.createElement('option', { value: 'active' }, 'Aktif')
            )
          ),

          React.createElement('div', { className: 'row' },
            React.createElement('div', { className: 'label' }, 'Kontrol aralığı (dk)'),
            React.createElement(
              'select',
              {
                value: String((state && state.captcha_check_interval) || 5),
                onChange: (e) => setField('captcha_check_interval', Number(e.target.value)),
                disabled: !(state && state.captcha_enabled),
              },
              React.createElement('option', { value: '5' }, '5 dk'),
              React.createElement('option', { value: '10' }, '10 dk'),
              React.createElement('option', { value: '20' }, '20 dk'),
              React.createElement('option', { value: '30' }, '30 dk')
            )
          ),

          React.createElement('div', { className: 'small' },
            ready ? 'Bağlantı: OK' : 'Bağlantı: bekleniyor...'
          )
        )
      ),

      React.createElement(
        'div',
        { className: 'card' },
        React.createElement(
          'div',
          { className: 'card-h' },
          React.createElement('h3', null, 'Durum')
        ),
        React.createElement(
          'div',
          { className: 'card-b' },
          React.createElement(
            'div',
            { className: 'log', id: 'log', ref: logRef },
            log.length
              ? log.map((l, idx) => React.createElement('div', { className: 'log-line', key: idx }, l))
              : React.createElement('div', { className: 'small' }, 'Log bekleniyor...')
          ),
          React.createElement(
            'div',
            { className: 'kpi' },
            React.createElement(
              'div',
              { className: 'box' },
              React.createElement('div', { className: 'num' }, String((state && state.attack_count) || 0)),
              React.createElement('div', { className: 'cap' }, 'Saldırı')
            ),
            React.createElement(
              'div',
              { className: 'box' },
              React.createElement('div', { className: 'num' }, String((state && state.rotation_counter) || 0)),
              React.createElement('div', { className: 'cap' }, 'Kamera dönüşü')
            )
          ),
          
          React.createElement('div', { className: 'preset-section' },
            React.createElement('div', { className: 'preset-header' }, '💾 Ayar Kayıtları'),
            React.createElement('div', { className: 'preset-save' },
              React.createElement('input', {
                className: 'input preset-input',
                type: 'text',
                placeholder: 'Kayıt ismi...',
                value: presetName,
                onChange: (e) => setPresetName(e.target.value),
                onKeyDown: (e) => { if (e.key === 'Enter') onSavePreset(); }
              }),
              React.createElement('button', { 
                className: 'btn preset-btn', 
                onClick: onSavePreset,
                disabled: !presetName.trim()
              }, '💾 Kaydet')
            ),
            presets.length > 0 
              ? React.createElement('div', { className: 'preset-list' },
                  presets.map((name) => 
                    React.createElement('div', { className: 'preset-item', key: name },
                      React.createElement('span', { className: 'preset-name' }, name),
                      React.createElement('div', { className: 'preset-actions' },
                        React.createElement('button', { 
                          className: 'preset-load', 
                          onClick: () => onLoadPreset(name),
                          title: 'Yükle'
                        }, '📂'),
                        React.createElement('button', { 
                          className: 'preset-delete', 
                          onClick: () => onDeletePreset(name),
                          title: 'Sil'
                        }, '🗑️')
                      )
                    )
                  )
                )
              : React.createElement('div', { className: 'small preset-empty' }, 'Henüz kayıt yok')
          )
        )
      )
    )
  );
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(React.createElement(App));

window.__TRITONX_APP_STARTED = true;
