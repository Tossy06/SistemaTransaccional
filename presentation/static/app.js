/* Comportamiento común de la interfaz. Guías aplicadas (modern-web-guidance):
   validate-input-after-interaction, accessible-error-announcement, autofill-sign-in-form,
   responsive-table y dialog. Todo funciona sin este archivo; solo mejora la experiencia. */
(() => {
  'use strict';

  /* ---------------------------------------------------------------- validación
     El error se muestra con :user-invalid (después de interactuar) y aquí se
     sincroniza aria-invalid, se enlaza el mensaje y se anuncia una sola vez. */
  const CAMPOS = 'input:not([type=hidden]):not([type=file]), select, textarea';
  let consecutivo = 0;

  const textoError = (el) => {
    if (el.validity.valueMissing && el.dataset.mensajeVacio) return el.dataset.mensajeVacio;
    if (el.validity.customError) return el.validationMessage;
    return el.dataset.mensaje || el.validationMessage;
  };

  // Cada campo con restricciones recibe su mensaje (id en data-error) justo después.
  const prepararCampo = (el) => {
    const tieneReglas = el.required || el.pattern || el.minLength > 0 || el.type === 'email' || el.dataset.igualA;
    if (!tieneReglas || el.dataset.error) return;
    const msg = document.createElement('span');
    msg.className = 'error-campo';
    msg.id = `error-${el.name || 'campo'}-${++consecutivo}`;
    msg.innerHTML = '<span class="icono-error" role="img" aria-label="Error">!</span><span class="texto"></span>';
    if (el.type === 'checkbox' && el.closest('label')) el.closest('label').append(msg);
    else (el.closest('.clave') || el).after(msg);
    el.dataset.error = msg.id;
  };

  // Enlaza el mensaje en aria-describedby solo mientras el campo es inválido.
  const enlazarError = (el, visible) => {
    const id = el.dataset.error;
    if (!id) return;
    const ids = (el.getAttribute('aria-describedby') || '').split(/\s+/).filter((x) => x && x !== id);
    if (visible) ids.push(id);
    if (ids.length) el.setAttribute('aria-describedby', ids.join(' '));
    else el.removeAttribute('aria-describedby');
  };

  const anunciador = document.createElement('div');
  anunciador.setAttribute('aria-live', 'polite');
  anunciador.className = 'visually-hidden';
  let temporizador, campoAnunciado;
  const anunciar = (el) => {
    const etiqueta = el.labels?.[0]?.childNodes[0]?.textContent.trim();
    clearTimeout(temporizador);
    anunciador.textContent = '';
    campoAnunciado = el;
    temporizador = setTimeout(() => {
      anunciador.textContent = `${etiqueta ? etiqueta + ': ' : ''}Error: ${textoError(el)}`;
    }, 500);
  };

  const marcados = new WeakSet();
  const anunciados = new WeakSet();
  const sincronizar = (el, conAnuncio = false) => {
    if (!el.matches?.(CAMPOS)) return;
    if (el.dataset.igualA) {
      const otro = el.form?.elements[el.dataset.igualA];
      el.setCustomValidity(otro && el.value && otro.value !== el.value ? 'Las dos contraseñas no coinciden.' : '');
    }
    const invalido = el.matches(':user-invalid');
    const msg = el.dataset.error && document.getElementById(el.dataset.error);
    if (invalido) {
      if (msg) msg.querySelector('.texto').textContent = textoError(el);
      if (conAnuncio && !anunciados.has(el)) { anunciar(el); anunciados.add(el); }
      el.setAttribute('aria-invalid', 'true');
      enlazarError(el, true);
      marcados.add(el);
    } else if (marcados.has(el) || el.getAttribute('aria-invalid') !== 'true') {
      el.setAttribute('aria-invalid', 'false');
      enlazarError(el, false);
      marcados.delete(el);
      anunciados.delete(el);
      if (campoAnunciado === el) { clearTimeout(temporizador); anunciador.textContent = ''; }
    }
  };

  /* ---------------------------------------------------------------- contraseñas visibles */
  const botonMostrar = (input) => {
    const caja = document.createElement('span');
    caja.className = 'clave';
    input.before(caja);
    caja.append(input);
    // El botón vive dentro de la etiqueta: el campo conserva solo el texto de su etiqueta
    // como nombre accesible, sin sumarle el "Mostrar" del botón.
    const nombre = input.labels?.[0]?.childNodes[0]?.textContent.trim();
    if (nombre && !input.hasAttribute('aria-label')) input.setAttribute('aria-label', nombre);
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'ver-clave';
    b.textContent = 'Mostrar';
    b.setAttribute('aria-pressed', 'false');
    b.addEventListener('click', () => {
      const ver = input.type === 'password';
      input.type = ver ? 'text' : 'password';
      b.textContent = ver ? 'Ocultar' : 'Mostrar';
      b.setAttribute('aria-pressed', String(ver));
    });
    caja.append(b);
  };

  /* ---------------------------------------------------------------- tablas
     En pantallas angostas cada fila es una tarjeta; la etiqueta de cada dato sale
     del encabezado de su columna. */
  const etiquetarTabla = (tabla) => {
    const titulos = [...tabla.querySelectorAll('thead th')].map((th) => th.textContent.trim());
    tabla.querySelectorAll('tbody tr').forEach((tr) => {
      [...tr.children].forEach((celda, i) => {
        if (titulos[i] && celda.colSpan === 1) celda.dataset.label = titulos[i];
      });
    });
  };

  /* ---------------------------------------------------------------- confirmaciones
     Botones con data-confirmar abren un <dialog> modal antes de enviar su formulario. */
  const dialogo = () => document.getElementById('confirmar');
  const confirmar = (evento) => {
    const boton = evento.submitter;
    if (!boton?.dataset.confirmar || boton.form.dataset.confirmado === 'si') return;
    evento.preventDefault();
    const d = dialogo();
    d.querySelector('#confirmar-titulo').textContent = boton.dataset.confirmar;
    d.querySelector('#confirmar-detalle').textContent = boton.dataset.detalle || '';
    const ok = d.querySelector('[value=confirmar]');
    ok.textContent = boton.textContent.trim();
    ok.className = boton.classList.contains('peligro') ? 'peligro' : '';
    d.returnValue = '';
    d.addEventListener('close', () => {
      if (d.returnValue === 'confirmar') {
        boton.form.dataset.confirmado = 'si';
        boton.form.requestSubmit(boton);
      }
      d.returnValue = '';
    }, { once: true });
    d.showModal();
  };

  document.addEventListener('DOMContentLoaded', () => {
    document.body.append(anunciador);
    document.querySelectorAll('input[type=password]').forEach(botonMostrar);
    document.querySelectorAll(CAMPOS).forEach((el) => { prepararCampo(el); sincronizar(el); });
    document.querySelectorAll('.hoja table').forEach(etiquetarTabla);
    document.querySelectorAll('[data-abre]').forEach((b) => b.addEventListener('click', () => {
      document.getElementById(b.dataset.abre).showModal();
    }));
  });
  document.addEventListener('blur', (e) => sincronizar(e.target, true), true);
  document.addEventListener('input', (e) => {
    if (e.target.hasAttribute?.('aria-invalid')) sincronizar(e.target);
    // Si cambia la contraseña, se revisa de nuevo su confirmación.
    const confirma = e.target.form?.querySelector(`[data-igual-a="${e.target.name}"]`);
    if (confirma) sincronizar(confirma);
  });
  document.addEventListener('change', (e) => sincronizar(e.target, true), true);
  document.addEventListener('invalid', (e) => { anunciados.add(e.target); sincronizar(e.target); }, true);
  document.addEventListener('submit', (e) => {
    // La regla de coincidencia se evalúa antes de que el navegador valide el envío.
    e.target.querySelectorAll('[data-igual-a]').forEach((el) => sincronizar(el));
    confirmar(e);
  });
})();

/* ======================================================================
   Cajón de navegación que en escritorio es barra lateral
   (guía navigation-drawer, variante "drawer that also acts as a sidebar").
   ====================================================================== */
(() => {
  'use strict';
  const drawer = document.getElementById('drawer');
  if (!drawer) return;
  const openBtn = document.getElementById('drawer-open');
  const closeBtn = document.getElementById('drawer-close');
  const scroller = drawer.querySelector('.Drawer-scroller');
  const sheet = drawer.querySelector('.Drawer-sheet');
  const fuera = [document.querySelector('main'), document.querySelector('.barra-movil')].filter(Boolean);
  const escritorio = matchMedia('(width >= 65em)');

  async function abrir() {
    drawer.showPopover();
    fuera.forEach((el) => { el.inert = true; });
    drawer.setAttribute('aria-modal', 'true');
    if (!CSS.supports('scroll-initial-target', 'nearest')) {
      // Respaldo: llevar el cajón a la posición cerrada para que entre deslizándose.
      scroller.scrollTo({left: scroller.offsetWidth, behavior: 'instant'});
      await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
    }
    scroller.scrollTo({left: 0, behavior: 'auto'});
    closeBtn.focus({preventScroll: true});
  }
  function cerrar() { scroller.scrollTo({left: scroller.offsetWidth, behavior: 'auto'}); }

  function alAbrir() { openBtn.setAttribute('aria-expanded', 'true'); }
  function alCerrar() {
    if (!drawer.hasAttribute('aria-modal')) return;  // el observador también avisa al cargar
    drawer.hidePopover();
    fuera.forEach((el) => { el.inert = false; });
    drawer.removeAttribute('aria-modal');
    openBtn.setAttribute('aria-expanded', 'false');
    openBtn.focus();
  }

  const umbral = 1 / window.innerWidth;
  new IntersectionObserver((entradas) => {
    if (escritorio.matches) return;
    const e = entradas.at(-1);
    if (e.intersectionRatio < umbral) alCerrar();
    if (e.intersectionRatio === 1) alAbrir();
  }, {root: drawer, threshold: [umbral, 1]}).observe(sheet);

  if (!CSS.supports('animation-timeline: scroll()')) {
    scroller.addEventListener('scroll', () => {
      drawer.style.setProperty('--drawer-backdrop', 1 - scroller.scrollLeft / sheet.offsetWidth);
    });
  }

  openBtn.addEventListener('click', abrir);
  closeBtn.addEventListener('click', cerrar);
  drawer.addEventListener('click', (e) => { if (!escritorio.matches && !sheet.contains(e.target)) cerrar(); });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && drawer.hasAttribute('aria-modal')) cerrar();
  });

  // En escritorio es una barra lateral, no un diálogo: se quita el role y se deshace el modo modal.
  function adaptar() {
    if (escritorio.matches) {
      drawer.removeAttribute('role');
      if (drawer.hasAttribute('aria-modal')) {
        if (drawer.matches(':popover-open')) drawer.hidePopover();
        fuera.forEach((el) => { el.inert = false; });
        drawer.removeAttribute('aria-modal');
        openBtn.setAttribute('aria-expanded', 'false');
      }
    } else {
      drawer.setAttribute('role', 'dialog');
    }
  }
  escritorio.addEventListener('change', adaptar);
  adaptar();
})();

/* ======================================================================
   Salida animada de los diálogos donde el navegador no anima display/overlay
   (guía animate-to-from-top-layer, "Top-layer exit fallback").
   ====================================================================== */
(() => {
  'use strict';
  let soporta;
  function puedeTransicionarDisplay() {
    if (soporta !== undefined) return soporta;
    if (!window.CSS?.supports?.('transition-behavior', 'allow-discrete') || !document.body) return (soporta = false);
    const p = document.createElement('div');
    p.style.cssText = 'transition: display 1s allow-discrete !important; display: block;';
    document.body.appendChild(p);
    getComputedStyle(p).display;
    p.style.display = 'none';
    soporta = getComputedStyle(p).display === 'block';
    p.remove();
    return soporta;
  }
  const salidaNativa = () => window.CSS?.supports?.('overlay', 'auto') && puedeTransicionarDisplay();

  async function cerrarAnimado(dialogo, valor) {
    if (!salidaNativa()) {
      dialogo.setAttribute('data-closing', '');
      const animaciones = dialogo.getAnimations({subtree: true});
      if (animaciones.length) {
        await Promise.race([Promise.allSettled(animaciones.map((a) => a.finished)),
                            new Promise((r) => setTimeout(r, 600))]);
      }
      dialogo.removeAttribute('data-closing');
    }
    dialogo.close(valor);
  }
  // Botones que cierran el diálogo (form method="dialog" o formmethod="dialog").
  document.addEventListener('click', (e) => {
    const b = e.target.closest('dialog.confirmacion button');
    if (!b || salidaNativa()) return;
    const porDialogo = b.form?.method === 'dialog' || b.getAttribute('formmethod') === 'dialog';
    if (!porDialogo) return;
    e.preventDefault();
    cerrarAnimado(b.closest('dialog'), b.value);
  });
  document.addEventListener('cancel', (e) => {
    if (!e.target.matches?.('dialog.confirmacion') || salidaNativa() || !e.cancelable) return;
    e.preventDefault();
    cerrarAnimado(e.target, '');
  }, true);
})();
