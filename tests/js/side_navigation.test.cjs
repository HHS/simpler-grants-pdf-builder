const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { join } = require('node:path');
const { runInNewContext } = require('node:vm');

const template = readFileSync(join(__dirname,
  '../../nofos/bloom_nofos/templates/includes/side_navigation.html'), 'utf8');
const source = template.match(/<script>([\s\S]*?)<\/script>/)[1];

function setup({ width = 1280, initialScroll = 0 } = {}) {
  function element(id) {
    const classes = new Set();
    return {
      attributes: { 'data-section-id': id },
      listeners: {},
      classList: {
        add: (name) => classes.add(name),
        remove: (name) => classes.delete(name),
        contains: (name) => classes.has(name),
      },
      getAttribute(name) { return this.attributes[name]; },
      setAttribute(name, value) { this.attributes[name] = value; },
      addEventListener(name, fn) { this.listeners[name] = fn; },
      focus() { document.activeElement = this; },
    };
  }

  const ids = ['basic', 'step-1', 'step-2', 'step-3'];
  const positions = [400, 1200, 2400.4, 3600];
  const links = ids.map(element);
  const pipes = ids.map(element);
  const elements = Object.fromEntries([
    'side-nav-container', 'side-nav-content', 'side-nav-toggle',
    'side-nav-close', 'side-nav-list',
  ].map((id) => [id, element(id)]));
  elements['side-nav-list'].querySelectorAll = () => links;
  elements['side-nav-list'].querySelector = () => links[0];
  elements['side-nav-container'].contains = (el) =>
    links.includes(el) || el === elements['side-nav-close'];
  const timers = new Map();
  const scrollListeners = {};
  let destination;
  const window = {
    pageYOffset: initialScroll,
    innerWidth: width,
    scrollTo(x, y) {
      if (typeof x === 'object') destination = x.top;
      else this.pageYOffset = y;
    },
    addEventListener(name, fn) { scrollListeners[name] = fn; },
  };
  const headings = ids.map((id, i) => ({
    getAttribute: () => id,
    // Captions stick at 85px plus the heading's 20px margin until
    // the next table pushes them out of view.
    getBoundingClientRect: () => ({
      top: Math.min(
        Math.max(105, positions[i] - window.pageYOffset),
        (positions[i + 1] ?? Infinity) - window.pageYOffset - 60,
      ),
    }),
  }));
  const document = {
    body: {},
    documentElement: { scrollTop: 0 },
    addEventListener(name, fn) { if (name === 'DOMContentLoaded') fn(); },
    getElementById: (id) => elements[id],
    querySelectorAll: (selector) => selector === 'h2[id]' ? headings : pipes,
  };
  runInNewContext(source, {
    document, window,
    setTimeout(fn) { const id = Symbol(); timers.set(id, fn); return id; },
    clearTimeout: (id) => timers.delete(id),
    MutationObserver: class { observe() {} },
  });

  return {
    links, pipes, window, elements,
    document,
    open() {
      elements['side-nav-toggle'].listeners.click();
      this.flush();
    },
    flush() {
      const pending = [...timers.values()];
      timers.clear();
      pending.forEach((fn) => fn());
    },
    click(i) { links[i].listeners.click.call(links[i], { preventDefault() {} }); },
    settle() { this.scroll(Math.round(destination)); },
    scroll(top) {
      window.pageYOffset = top;
      scrollListeners.scroll();
      const pending = [...timers.values()];
      timers.clear();
      pending.forEach((fn) => fn());
    },
    assertCurrent(i) {
      assert.deepEqual(links.map((link) => link.classList.contains('usa-current')),
        ids.map((_, index) => index === i));
      assert.deepEqual(pipes.map((pipe) => pipe.classList.contains('current')),
        ids.map((_, index) => index === i));
    },
  };
}

test('jump-to highlighting survives smooth scrolling and sticky captions', () => {
  const nav = setup();
  nav.assertCurrent(-1);
  for (const i of [1, 2, 3, 0, 2]) {
    nav.click(i);
    nav.assertCurrent(i);
    nav.settle();
    nav.assertCurrent(i);
  }
});

test('manual scrolling updates both indicators in either direction', () => {
  const nav = setup();
  for (const [position, active] of [[1400, 1], [2800, 2], [4200, 3], [1500, 1], [0, -1]]) {
    nav.scroll(position);
    nav.assertCurrent(active);
  }
});

test('restored scroll position selects the section despite sticky headings', () => {
  const nav = setup({ initialScroll: 2800 });
  assert.equal(nav.window.pageYOffset, 2800);
  nav.assertCurrent(2);
});

test('mobile jump-to closes navigation and retains the selected indicators', () => {
  const nav = setup({ width: 375 });
  nav.open();
  assert.equal(nav.elements['side-nav-toggle'].getAttribute('aria-expanded'), 'true');
  nav.click(2);
  assert.equal(nav.elements['side-nav-toggle'].getAttribute('aria-expanded'), 'false');
  nav.settle();
  nav.assertCurrent(2);
});

test('mobile navigation reopens after a jump when Safari blurs the tapped toggle', () => {
  const nav = setup({ width: 375 });
  const toggle = nav.elements['side-nav-toggle'];
  nav.open();
  nav.click(2);
  assert.equal(nav.document.activeElement, toggle);

  // iOS Safari does not focus a tapped button: the focused toggle blurs to
  // <body> before the click handler opens the navigation.
  nav.document.activeElement = nav.document.body;
  nav.elements['side-nav-container'].listeners.focusout({});
  toggle.listeners.click();
  nav.flush();

  assert.equal(toggle.getAttribute('aria-expanded'), 'true');
  assert.ok(nav.elements['side-nav-container'].classList.contains('is-open'));
});
