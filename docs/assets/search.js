/* PyDocGen client-side search */
(function () {
  'use strict';

  var input = document.getElementById('search-input');
  var index = null;
  var dropdown = null;

  // Determine root prefix from current page depth
  var depth = (window.location.pathname.match(/\//g) || []).length - 1;
  var prefix = '';
  for (var i = 0; i < depth; i++) prefix += '../';

  function loadIndex() {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', prefix + 'search_index.json', true);
    xhr.onload = function () {
      if (xhr.status === 200) {
        try { index = JSON.parse(xhr.responseText); } catch (e) {}
      }
    };
    xhr.send();
  }

  function createDropdown() {
    dropdown = document.createElement('ul');
    dropdown.id = 'search-results';
    dropdown.style.cssText =
      'position:absolute;top:100%;right:0;background:#fff;border:1px solid #ccc;' +
      'border-radius:4px;list-style:none;padding:4px 0;margin:0;min-width:280px;' +
      'max-height:320px;overflow-y:auto;z-index:9999;box-shadow:0 4px 12px rgba(0,0,0,.15)';
    input.parentNode.style.position = 'relative';
    input.parentNode.appendChild(dropdown);
  }

  function showResults(results) {
    if (!dropdown) createDropdown();
    dropdown.innerHTML = '';
    if (!results.length) {
      var li = document.createElement('li');
      li.textContent = 'No results';
      li.style.cssText = 'padding:8px 14px;color:#999;font-size:13px';
      dropdown.appendChild(li);
    } else {
      results.slice(0, 12).forEach(function (r) {
        var li = document.createElement('li');
        var a = document.createElement('a');
        a.href = prefix + r.url;
        a.textContent = r.title;
        a.style.cssText =
          'display:block;padding:6px 14px;color:#1d6fa4;text-decoration:none;font-size:13px';
        a.onmouseover = function () { a.style.background = '#f0f4f8'; };
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
    if (!index || !query) { hideResults(); return; }
    var q = query.toLowerCase();
    var results = index.filter(function (e) {
      return e.title.toLowerCase().indexOf(q) !== -1;
    });
    showResults(results);
  }

  document.addEventListener('DOMContentLoaded', function () {
    loadIndex();
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
}());
