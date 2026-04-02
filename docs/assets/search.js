/* PyDocGen client-side search */
(function () {
  'use strict';

  var input = document.getElementById('search-input');
  var dropdown = null;

  // Get embedded search index from window (set by layout.py after this script loads)
  function getIndex() {
    return window.__SEARCH_INDEX__ || [];
  }

  // Get embedded search prefix from window (set by layout.py)
  function getPrefix() {
    return window.__SEARCH_PREFIX__ || '';
  }

  function createDropdown() {
    dropdown = document.createElement('ul');
    dropdown.id = 'search-results';
    dropdown.style.cssText =
      'position:absolute;top:100%;left:0;right:0;background:#252525;border:1px solid #444;' +
      'border-radius:4px;list-style:none;padding:4px 0;margin:0;width:100%;' +
      'max-height:320px;overflow-y:auto;z-index:9999;box-shadow:0 4px 12px rgba(0,0,0,.4)';
    input.parentNode.style.position = 'relative';
    input.parentNode.appendChild(dropdown);
  }

  function showResults(results) {
    if (!dropdown) createDropdown();
    dropdown.innerHTML = '';
    if (!results.length) {
      var li = document.createElement('li');
      li.textContent = 'No results';
      li.style.cssText = 'padding:8px 14px;color:#888;font-size:14px';
      dropdown.appendChild(li);
    } else {
      results.slice(0, 12).forEach(function (r) {
        var li = document.createElement('li');
        var a = document.createElement('a');
        a.href = getPrefix() + r.url;
        a.textContent = r.title;
        a.style.cssText =
          'display:block;padding:6px 14px;color:#e3e3e3;text-decoration:none;font-size:14px';
        a.onmouseover = function () { a.style.background = '#3a3a3a'; };
        a.onmouseout = function () { a.style.background = ''; };
        li.appendChild(a);
        dropdown.appendChild(li);
      });
    }
    dropdown.style.display = 'block';
  }

  function hideResults() {
    if (dropdown) dropdown.style.display = 'none';
  }

  function search(query) {
    var index = getIndex();
    if (!index || !query) { hideResults(); return; }
    var q = query.toLowerCase();
    var results = index.filter(function (e) {
      return e.title.toLowerCase().indexOf(q) !== -1;
    });
    showResults(results);
  }

  document.addEventListener('DOMContentLoaded', function () {
    if (!input) return;

    input.addEventListener('input', function () { search(this.value.trim()); });
    input.addEventListener('focus', function () { if (this.value.trim()) search(this.value.trim()); });

    document.addEventListener('click', function (e) {
      if (input && !input.parentNode.contains(e.target)) hideResults();
    });
  });

  // Highlight current section on scroll (right sidebar)
  document.addEventListener('DOMContentLoaded', function () {
    var links = document.querySelectorAll('.contents-sidebar a');
    if (!links.length) return;

    function onScroll() {
      var scrollY = window.scrollY + 80;
      var current = null;
      links.forEach(function (a) {
        var id = a.getAttribute('href').slice(1);
        var el = document.getElementById(id);
        if (el && el.offsetTop <= scrollY) current = a;
      });
      links.forEach(function (a) { a.classList.remove('current'); });
      if (current) current.classList.add('current');
    }

    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  });

  // Nav tree toggle (expand/collapse children without navigating)
  document.addEventListener('DOMContentLoaded', function () {
    var toggles = document.querySelectorAll('.nav-toggle');
    toggles.forEach(function (toggle) {
      toggle.addEventListener('click', function (e) {
        e.stopPropagation();
        var li = toggle.closest('.has-children');
        if (li) {
          li.classList.toggle('expanded');
          li.classList.toggle('collapsed');
          var childList = li.querySelector('.nav-children');
          if (childList) {
            childList.classList.toggle('expanded');
            childList.classList.toggle('collapsed');
          }
        }
      });
    });
  });
}());
