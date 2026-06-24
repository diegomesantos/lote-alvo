(function () {
  var DEBOUNCE_MS = 220;
  var MIN_QUERY_LENGTH = 2;

  function escapeHtml(value) {
    return String(value || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function getState(picker) {
    if (!picker.__loteAlvoUserPicker) {
      picker.__loteAlvoUserPicker = {
        results: [],
        activeIndex: -1,
        debounce: null,
        abortController: null,
        selectedUsername: '',
      };
    }
    return picker.__loteAlvoUserPicker;
  }

  function getParts(picker) {
    return {
      input: picker.querySelector('[data-user-picker-input]'),
      hidden: picker.querySelector('[data-user-picker-value]'),
      results: picker.querySelector('[data-user-picker-results]'),
      selected: picker.querySelector('[data-user-picker-selected]'),
      status: picker.querySelector('[data-user-picker-status]'),
    };
  }

  function setExpanded(input, expanded) {
    if (input) {
      input.setAttribute('aria-expanded', expanded ? 'true' : 'false');
    }
  }

  function closeResults(picker) {
    var parts = getParts(picker);
    var state = getState(picker);
    state.activeIndex = -1;
    if (parts.results) {
      parts.results.classList.add('hidden');
      parts.results.innerHTML = '';
    }
    setExpanded(parts.input, false);
  }

  function renderMessage(picker, message) {
    var parts = getParts(picker);
    if (!parts.results) return;
    parts.results.innerHTML = '<div class="px-3 py-2 text-sm text-gray-500">' + escapeHtml(message) + '</div>';
    parts.results.classList.remove('hidden');
    setExpanded(parts.input, true);
  }

  function renderSelected(picker, user) {
    var parts = getParts(picker);
    if (!parts.selected) return;
    parts.selected.innerHTML = [
      '<div class="flex items-center gap-2">',
      '<span class="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-teal-600 text-[11px] font-bold text-white">',
      escapeHtml(user.initials || user.username || '?'),
      '</span>',
      '<span class="min-w-0">',
      '<span class="block truncate font-semibold">', escapeHtml(user.label || user.username), '</span>',
      '<span class="block truncate text-teal-700">', escapeHtml(user.meta || ('@' + user.username)), '</span>',
      '</span>',
      '</div>'
    ].join('');
    parts.selected.classList.remove('hidden');
  }

  function clearSelected(picker, keepInput) {
    var parts = getParts(picker);
    var state = getState(picker);
    state.selectedUsername = '';
    if (parts.hidden) {
      parts.hidden.value = '';
    }
    if (!keepInput && parts.input) {
      parts.input.value = '';
    }
    if (parts.selected) {
      parts.selected.classList.add('hidden');
      parts.selected.innerHTML = '';
    }
  }

  function selectUser(picker, user) {
    var parts = getParts(picker);
    var state = getState(picker);
    if (parts.hidden) {
      parts.hidden.value = user.id;
    }
    if (parts.input) {
      parts.input.value = '@' + user.username;
      parts.input.setCustomValidity('');
    }
    state.selectedUsername = user.username;
    renderSelected(picker, user);
    closeResults(picker);
  }

  function renderResults(picker, users) {
    var parts = getParts(picker);
    var state = getState(picker);
    if (!parts.results) return;

    state.results = users || [];
    state.activeIndex = users && users.length ? 0 : -1;

    if (!users || !users.length) {
      renderMessage(picker, 'Nenhum usuário encontrado.');
      return;
    }

    parts.results.innerHTML = users.map(function (user, index) {
      var activeClass = index === state.activeIndex ? ' bg-teal-50 text-teal-900' : ' text-gray-800';
      return [
        '<button type="button" role="option" data-user-picker-option="', index, '"',
        ' class="flex w-full items-center gap-3 px-3 py-2 text-left text-sm transition hover:bg-teal-50', activeClass, '">',
        '<span class="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-gray-100 text-xs font-bold text-gray-600">',
        escapeHtml(user.initials || user.username || '?'),
        '</span>',
        '<span class="min-w-0">',
        '<span class="block truncate font-semibold">', escapeHtml(user.label || user.username), '</span>',
        '<span class="block truncate text-xs text-gray-500">', escapeHtml(user.meta || ('@' + user.username)), '</span>',
        '</span>',
        '</button>'
      ].join('');
    }).join('');

    parts.results.classList.remove('hidden');
    setExpanded(parts.input, true);
  }

  function updateActiveOption(picker) {
    var parts = getParts(picker);
    var state = getState(picker);
    if (!parts.results) return;
    parts.results.querySelectorAll('[data-user-picker-option]').forEach(function (button) {
      var index = Number(button.dataset.userPickerOption);
      var isActive = index === state.activeIndex;
      button.classList.toggle('bg-teal-50', isActive);
      button.classList.toggle('text-teal-900', isActive);
      button.classList.toggle('text-gray-800', !isActive);
      if (isActive) {
        button.scrollIntoView({ block: 'nearest' });
      }
    });
  }

  function queryUsers(picker, query) {
    var parts = getParts(picker);
    var state = getState(picker);
    var searchUrl = picker.dataset.searchUrl;
    if (!searchUrl || !parts.input) return;

    if (!query || (query.charAt(0) !== '@' && query.length < MIN_QUERY_LENGTH)) {
      closeResults(picker);
      return;
    }

    if (state.abortController) {
      state.abortController.abort();
    }
    state.abortController = window.AbortController ? new AbortController() : null;

    if (parts.status) {
      parts.status.textContent = '...';
    }

    var separator = searchUrl.indexOf('?') === -1 ? '?' : '&';
    fetch(searchUrl + separator + 'q=' + encodeURIComponent(query), {
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
      signal: state.abortController ? state.abortController.signal : undefined,
    })
      .then(function (response) {
        if (!response.ok) throw new Error('search_failed');
        return response.json();
      })
      .then(function (data) {
        renderResults(picker, data.results || []);
      })
      .catch(function (error) {
        if (error.name === 'AbortError') return;
        renderMessage(picker, 'Não foi possível buscar usuários agora.');
      })
      .finally(function () {
        if (parts.status) {
          parts.status.textContent = '@';
        }
      });
  }

  function scheduleSearch(picker) {
    var parts = getParts(picker);
    var state = getState(picker);
    if (!parts.input) return;

    clearTimeout(state.debounce);
    state.debounce = setTimeout(function () {
      queryUsers(picker, parts.input.value.trim());
    }, DEBOUNCE_MS);
  }

  function bindFormValidation(form) {
    if (!form || form.dataset.userPickerSubmitBound) return;
    form.dataset.userPickerSubmitBound = '1';
    form.addEventListener('submit', function (event) {
      var invalidInput = null;
      form.querySelectorAll('[data-user-picker]').forEach(function (picker) {
        var parts = getParts(picker);
        if (!parts.input || !parts.hidden || parts.hidden.value) return;
        parts.input.setCustomValidity(parts.input.dataset.userPickerRequiredMessage || 'Selecione um usuário da lista.');
        invalidInput = invalidInput || parts.input;
      });
      if (invalidInput) {
        event.preventDefault();
        invalidInput.reportValidity();
      }
    });
  }

  function initPicker(picker) {
    if (!picker || picker.dataset.userPickerReady) return;
    picker.dataset.userPickerReady = '1';

    var parts = getParts(picker);
    var state = getState(picker);
    if (!parts.input || !parts.hidden || !parts.results) return;

    parts.input.addEventListener('input', function () {
      if (state.selectedUsername && this.value !== '@' + state.selectedUsername) {
        clearSelected(picker, true);
      }
      this.setCustomValidity('');
      scheduleSearch(picker);
    });

    parts.input.addEventListener('focus', function () {
      if (this.value.trim() === '@') {
        queryUsers(picker, '@');
      }
    });

    parts.input.addEventListener('keydown', function (event) {
      var results = getState(picker).results;
      if (!results.length) return;

      if (event.key === 'ArrowDown') {
        event.preventDefault();
        state.activeIndex = (state.activeIndex + 1) % results.length;
        updateActiveOption(picker);
      } else if (event.key === 'ArrowUp') {
        event.preventDefault();
        state.activeIndex = (state.activeIndex - 1 + results.length) % results.length;
        updateActiveOption(picker);
      } else if (event.key === 'Enter') {
        if (!parts.results.classList.contains('hidden') && state.activeIndex >= 0) {
          event.preventDefault();
          selectUser(picker, results[state.activeIndex]);
        }
      } else if (event.key === 'Escape') {
        closeResults(picker);
      }
    });

    parts.results.addEventListener('mousedown', function (event) {
      event.preventDefault();
    });

    parts.results.addEventListener('click', function (event) {
      var option = event.target.closest('[data-user-picker-option]');
      if (!option) return;
      var index = Number(option.dataset.userPickerOption);
      var user = getState(picker).results[index];
      if (user) {
        selectUser(picker, user);
      }
    });

    document.addEventListener('click', function (event) {
      if (!picker.contains(event.target)) {
        closeResults(picker);
      }
    });

    bindFormValidation(picker.closest('form'));
  }

  function initAll(root) {
    (root || document).querySelectorAll('[data-user-picker]').forEach(initPicker);
  }

  function reset(root) {
    var scope = root || document;
    var pickers = scope.matches && scope.matches('[data-user-picker]')
      ? [scope]
      : Array.from(scope.querySelectorAll ? scope.querySelectorAll('[data-user-picker]') : []);
    pickers.forEach(function (picker) {
      clearSelected(picker, false);
      closeResults(picker);
      var parts = getParts(picker);
      if (parts.input) {
        parts.input.setCustomValidity('');
      }
    });
  }

  function focus(root) {
    var scope = root || document;
    var picker = scope.matches && scope.matches('[data-user-picker]')
      ? scope
      : (scope.querySelector ? scope.querySelector('[data-user-picker]') : null);
    var parts = picker ? getParts(picker) : {};
    if (parts.input) {
      window.setTimeout(function () {
        parts.input.focus();
      }, 50);
    }
  }

  window.LoteAlvoUserPicker = {
    init: initAll,
    reset: reset,
    focus: focus,
  };

  document.addEventListener('DOMContentLoaded', function () {
    initAll(document);
  });
})();
