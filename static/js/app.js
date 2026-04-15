// FitLog Client-Side JavaScript
// Dynamic form handling, template loading, mobile menu, confirmations, validation

(function () {
  "use strict";

  // ============================================================
  // Utility Helpers
  // ============================================================

  function qs(selector, parent) {
    return (parent || document).querySelector(selector);
  }

  function qsa(selector, parent) {
    return Array.from((parent || document).querySelectorAll(selector));
  }

  function on(el, event, handler) {
    if (el) {
      el.addEventListener(event, handler);
    }
  }

  function delegate(parent, event, selector, handler) {
    if (!parent) return;
    parent.addEventListener(event, function (e) {
      var target = e.target.closest(selector);
      if (target && parent.contains(target)) {
        handler.call(target, e, target);
      }
    });
  }

  function createElement(tag, attrs, children) {
    var el = document.createElement(tag);
    if (attrs) {
      Object.keys(attrs).forEach(function (key) {
        if (key === "className") {
          el.className = attrs[key];
        } else if (key === "innerHTML") {
          el.innerHTML = attrs[key];
        } else if (key === "textContent") {
          el.textContent = attrs[key];
        } else {
          el.setAttribute(key, attrs[key]);
        }
      });
    }
    if (children) {
      children.forEach(function (child) {
        if (typeof child === "string") {
          el.appendChild(document.createTextNode(child));
        } else if (child) {
          el.appendChild(child);
        }
      });
    }
    return el;
  }

  // ============================================================
  // Mobile Hamburger Menu Toggle
  // ============================================================

  function initMobileMenu() {
    var toggleBtn = qs("[data-menu-toggle]");
    var menu = qs("[data-menu-target]");

    if (!toggleBtn || !menu) return;

    on(toggleBtn, "click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      var isOpen = !menu.classList.contains("hidden");
      if (isOpen) {
        menu.classList.add("hidden");
        toggleBtn.setAttribute("aria-expanded", "false");
      } else {
        menu.classList.remove("hidden");
        toggleBtn.setAttribute("aria-expanded", "true");
      }
    });

    on(document, "click", function (e) {
      if (
        !menu.classList.contains("hidden") &&
        !menu.contains(e.target) &&
        !toggleBtn.contains(e.target)
      ) {
        menu.classList.add("hidden");
        toggleBtn.setAttribute("aria-expanded", "false");
      }
    });
  }

  // ============================================================
  // Delete Confirmation Dialogs
  // ============================================================

  function initDeleteConfirmations() {
    delegate(document.body, "click", "[data-confirm-delete]", function (e, el) {
      var message =
        el.getAttribute("data-confirm-delete") ||
        "Are you sure you want to delete this? This action cannot be undone.";
      if (!confirm(message)) {
        e.preventDefault();
        e.stopPropagation();
      }
    });

    delegate(document.body, "submit", "form[data-confirm-submit]", function (e, form) {
      var message =
        form.getAttribute("data-confirm-submit") ||
        "Are you sure you want to proceed?";
      if (!confirm(message)) {
        e.preventDefault();
        e.stopPropagation();
      }
    });
  }

  // ============================================================
  // Form Validation Helpers
  // ============================================================

  function initFormValidation() {
    var forms = qsa("form[data-validate]");
    forms.forEach(function (form) {
      on(form, "submit", function (e) {
        clearValidationErrors(form);
        var isValid = validateForm(form);
        if (!isValid) {
          e.preventDefault();
          e.stopPropagation();
        }
      });
    });
  }

  function validateForm(form) {
    var valid = true;
    var requiredFields = qsa("[required]", form);
    requiredFields.forEach(function (field) {
      if (!field.value || !field.value.trim()) {
        showFieldError(field, "This field is required.");
        valid = false;
      }
    });

    var emailFields = qsa('input[type="email"]', form);
    emailFields.forEach(function (field) {
      if (field.value && !isValidEmail(field.value)) {
        showFieldError(field, "Please enter a valid email address.");
        valid = false;
      }
    });

    var passwordField = qs('input[name="password"]', form);
    var confirmField = qs('input[name="confirm_password"]', form);
    if (passwordField && confirmField) {
      if (passwordField.value && passwordField.value.length < 8) {
        showFieldError(passwordField, "Password must be at least 8 characters.");
        valid = false;
      }
      if (
        confirmField.value &&
        passwordField.value !== confirmField.value
      ) {
        showFieldError(confirmField, "Passwords do not match.");
        valid = false;
      }
    }

    return valid;
  }

  function isValidEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  }

  function showFieldError(field, message) {
    field.classList.add("border-red-500", "ring-red-500");
    field.classList.remove("border-gray-300");
    var errorEl = createElement("p", {
      className: "text-red-500 text-sm mt-1 field-error",
      textContent: message,
    });
    field.parentNode.appendChild(errorEl);
  }

  function clearValidationErrors(form) {
    qsa(".field-error", form).forEach(function (el) {
      el.remove();
    });
    qsa(".border-red-500", form).forEach(function (el) {
      el.classList.remove("border-red-500", "ring-red-500");
      el.classList.add("border-gray-300");
    });
  }

  // ============================================================
  // Workout Form: Exercise & Set Management
  // ============================================================

  var exerciseIndex = 0;

  function getNextExerciseIndex() {
    var container = qs("#exercises-container");
    if (!container) return 0;
    var existing = qsa("[data-exercise-index]", container);
    var maxIdx = -1;
    existing.forEach(function (el) {
      var idx = parseInt(el.getAttribute("data-exercise-index"), 10);
      if (idx > maxIdx) maxIdx = idx;
    });
    return maxIdx + 1;
  }

  function initWorkoutForm() {
    var container = qs("#exercises-container");
    var addExerciseBtn = qs("#add-exercise-btn");

    if (!container || !addExerciseBtn) return;

    exerciseIndex = getNextExerciseIndex();
    if (exerciseIndex === 0) exerciseIndex = 0;

    on(addExerciseBtn, "click", function (e) {
      e.preventDefault();
      addExerciseRow(container);
    });

    delegate(container, "click", ".remove-exercise-btn", function (e, btn) {
      e.preventDefault();
      var exerciseRow = btn.closest("[data-exercise-index]");
      if (exerciseRow) {
        exerciseRow.remove();
        renumberExercises(container);
      }
    });

    delegate(container, "click", ".add-set-btn", function (e, btn) {
      e.preventDefault();
      var exerciseRow = btn.closest("[data-exercise-index]");
      if (exerciseRow) {
        var exIdx = exerciseRow.getAttribute("data-exercise-index");
        addSetRow(exerciseRow, exIdx);
      }
    });

    delegate(container, "click", ".remove-set-btn", function (e, btn) {
      e.preventDefault();
      var setRow = btn.closest("[data-set-row]");
      var exerciseRow = btn.closest("[data-exercise-index]");
      if (setRow) {
        setRow.remove();
        if (exerciseRow) {
          renumberSets(exerciseRow);
        }
      }
    });

    initExerciseSearch(container);
  }

  function addExerciseRow(container, exerciseData) {
    var idx = exerciseIndex++;
    var sortOrder = qsa("[data-exercise-index]", container).length + 1;

    var exerciseOptions = getExerciseOptionsHTML();

    var selectedExerciseId =
      exerciseData && exerciseData.exercise_id
        ? exerciseData.exercise_id
        : "";
    var exerciseNotes =
      exerciseData && exerciseData.notes ? exerciseData.notes : "";

    var html =
      '<div class="bg-white border border-gray-200 rounded-lg p-4 mb-4" data-exercise-index="' +
      idx +
      '">' +
      '  <div class="flex items-center justify-between mb-3">' +
      '    <h4 class="text-lg font-semibold text-gray-700">Exercise <span class="exercise-number">' +
      sortOrder +
      "</span></h4>" +
      '    <button type="button" class="remove-exercise-btn text-red-500 hover:text-red-700 p-2 min-w-[44px] min-h-[44px] flex items-center justify-center" title="Remove exercise">' +
      '      <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>' +
      "    </button>" +
      "  </div>" +
      '  <input type="hidden" name="exercises[' +
      idx +
      '][sort_order]" value="' +
      sortOrder +
      '" class="sort-order-input">' +
      '  <div class="mb-3">' +
      '    <label class="block text-sm font-medium text-gray-700 mb-1">Exercise</label>' +
      '    <select name="exercises[' +
      idx +
      '][exercise_id]" class="exercise-select w-full border border-gray-300 rounded-md px-3 py-2 min-h-[44px]" required>' +
      '      <option value="">Select an exercise</option>' +
      exerciseOptions +
      "    </select>" +
      "  </div>" +
      '  <div class="mb-3">' +
      '    <label class="block text-sm font-medium text-gray-700 mb-1">Notes</label>' +
      '    <input type="text" name="exercises[' +
      idx +
      '][notes]" value="' +
      escapeAttr(exerciseNotes) +
      '" class="w-full border border-gray-300 rounded-md px-3 py-2 min-h-[44px]" placeholder="Exercise notes (optional)">' +
      "  </div>" +
      '  <div class="sets-container mb-3">' +
      '    <div class="flex items-center justify-between mb-2">' +
      '      <h5 class="text-sm font-semibold text-gray-600">Sets</h5>' +
      '      <button type="button" class="add-set-btn text-blue-600 hover:text-blue-800 text-sm font-medium p-2 min-w-[44px] min-h-[44px] flex items-center justify-center">+ Add Set</button>' +
      "    </div>" +
      '    <div class="sets-list">' +
      "    </div>" +
      "  </div>" +
      "</div>";

    var wrapper = createElement("div", { innerHTML: html });
    var exerciseEl = wrapper.firstElementChild;
    container.appendChild(exerciseEl);

    if (selectedExerciseId) {
      var select = qs(".exercise-select", exerciseEl);
      if (select) select.value = selectedExerciseId;
    }

    if (exerciseData && exerciseData.sets && exerciseData.sets.length > 0) {
      exerciseData.sets.forEach(function (setData) {
        addSetRow(exerciseEl, idx, setData);
      });
    } else {
      addSetRow(exerciseEl, idx);
    }

    return exerciseEl;
  }

  function addSetRow(exerciseEl, exerciseIdx, setData) {
    var setsList = qs(".sets-list", exerciseEl);
    if (!setsList) return;

    var existingSets = qsa("[data-set-row]", setsList);
    var setNumber = existingSets.length + 1;

    var weight = setData && setData.weight != null ? setData.weight : "";
    var reps = setData && setData.reps != null ? setData.reps : "";

    var html =
      '<div class="flex items-center gap-2 mb-2 p-2 bg-gray-50 rounded" data-set-row="' +
      setNumber +
      '">' +
      '  <span class="text-sm font-medium text-gray-500 w-8 set-number">' +
      setNumber +
      "</span>" +
      '  <input type="hidden" name="exercises[' +
      exerciseIdx +
      "][sets][" +
      (setNumber - 1) +
      '][set_number]" value="' +
      setNumber +
      '" class="set-number-input">' +
      '  <div class="flex-1">' +
      '    <input type="number" name="exercises[' +
      exerciseIdx +
      "][sets][" +
      (setNumber - 1) +
      '][weight]" value="' +
      weight +
      '" step="0.5" min="0" class="w-full border border-gray-300 rounded px-2 py-1 text-sm min-h-[44px]" placeholder="Weight (kg)">' +
      "  </div>" +
      '  <div class="flex-1">' +
      '    <input type="number" name="exercises[' +
      exerciseIdx +
      "][sets][" +
      (setNumber - 1) +
      '][reps]" value="' +
      reps +
      '" min="1" class="w-full border border-gray-300 rounded px-2 py-1 text-sm min-h-[44px]" placeholder="Reps" required>' +
      "  </div>" +
      '  <button type="button" class="remove-set-btn text-red-400 hover:text-red-600 p-1 min-w-[44px] min-h-[44px] flex items-center justify-center" title="Remove set">' +
      '    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>' +
      "  </button>" +
      "</div>";

    var wrapper = createElement("div", { innerHTML: html });
    setsList.appendChild(wrapper.firstElementChild);
  }

  function renumberExercises(container) {
    var exercises = qsa("[data-exercise-index]", container);
    exercises.forEach(function (el, i) {
      var numberSpan = qs(".exercise-number", el);
      if (numberSpan) numberSpan.textContent = i + 1;
      var sortInput = qs(".sort-order-input", el);
      if (sortInput) sortInput.value = i + 1;
    });
  }

  function renumberSets(exerciseEl) {
    var exIdx = exerciseEl.getAttribute("data-exercise-index");
    var sets = qsa("[data-set-row]", exerciseEl);
    sets.forEach(function (setEl, i) {
      var setNum = i + 1;
      setEl.setAttribute("data-set-row", setNum);
      var numberSpan = qs(".set-number", setEl);
      if (numberSpan) numberSpan.textContent = setNum;

      var setNumberInput = qs(".set-number-input", setEl);
      if (setNumberInput) {
        setNumberInput.value = setNum;
        setNumberInput.name =
          "exercises[" + exIdx + "][sets][" + i + "][set_number]";
      }

      var weightInput = qs('input[placeholder="Weight (kg)"]', setEl);
      if (weightInput) {
        weightInput.name =
          "exercises[" + exIdx + "][sets][" + i + "][weight]";
      }

      var repsInput = qs('input[placeholder="Reps"]', setEl);
      if (repsInput) {
        repsInput.name =
          "exercises[" + exIdx + "][sets][" + i + "][reps]";
      }
    });
  }

  function getExerciseOptionsHTML() {
    var sourceSelect = qs("#exercise-options-source");
    if (sourceSelect) {
      var options = "";
      qsa("option", sourceSelect).forEach(function (opt) {
        if (opt.value) {
          options +=
            '<option value="' +
            escapeAttr(opt.value) +
            '">' +
            escapeHTML(opt.textContent) +
            "</option>";
        }
      });
      return options;
    }

    if (window.__exerciseOptions) {
      return window.__exerciseOptions;
    }

    return "";
  }

  function escapeAttr(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function escapeHTML(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  // ============================================================
  // Exercise Search/Filter within Workout Form
  // ============================================================

  function initExerciseSearch(container) {
    delegate(container, "input", ".exercise-search-input", function (e, input) {
      var query = input.value.toLowerCase().trim();
      var exerciseRow = input.closest("[data-exercise-index]");
      var select = qs(".exercise-select", exerciseRow);
      if (!select) return;

      qsa("option", select).forEach(function (opt) {
        if (!opt.value) return;
        var text = opt.textContent.toLowerCase();
        opt.style.display = text.indexOf(query) !== -1 ? "" : "none";
      });
    });
  }

  // ============================================================
  // Template Selector
  // ============================================================

  function initTemplateSelector() {
    var templateSelect = qs("#template-selector");
    if (!templateSelect) return;

    on(templateSelect, "change", function () {
      var templateId = templateSelect.value;
      if (!templateId) return;

      loadTemplate(templateId);
    });
  }

  function loadTemplate(templateId) {
    var container = qs("#exercises-container");
    if (!container) return;

    var url = "/api/templates/" + encodeURIComponent(templateId);

    fetch(url, {
      method: "GET",
      headers: {
        Accept: "application/json",
      },
      credentials: "same-origin",
    })
      .then(function (response) {
        if (!response.ok) {
          throw new Error("Failed to load template (HTTP " + response.status + ")");
        }
        return response.json();
      })
      .then(function (data) {
        populateFromTemplate(container, data);
      })
      .catch(function (err) {
        console.error("Error loading template:", err);
        showNotification("Failed to load template. Please try again.", "error");
      });
  }

  function populateFromTemplate(container, templateData) {
    container.innerHTML = "";
    exerciseIndex = 0;

    if (!templateData.exercises || templateData.exercises.length === 0) {
      showNotification("This template has no exercises.", "warning");
      return;
    }

    var nameInput = qs('input[name="name"]');
    if (nameInput && templateData.name && !nameInput.value) {
      nameInput.value = templateData.name;
    }

    templateData.exercises.forEach(function (exercise) {
      var exerciseData = {
        exercise_id: exercise.exercise_id,
        notes: exercise.notes || "",
        sets: [],
      };

      var numSets = exercise.default_sets || exercise.sets || 3;
      var defaultReps = exercise.default_reps || exercise.reps || "";
      var defaultWeight = exercise.default_weight || exercise.weight || "";

      if (exercise.sets && Array.isArray(exercise.sets)) {
        exerciseData.sets = exercise.sets;
      } else {
        for (var s = 0; s < numSets; s++) {
          exerciseData.sets.push({
            set_number: s + 1,
            weight: defaultWeight,
            reps: defaultReps,
          });
        }
      }

      addExerciseRow(container, exerciseData);
    });

    showNotification("Template loaded successfully!", "success");
  }

  // ============================================================
  // Notification Helper
  // ============================================================

  function showNotification(message, type) {
    var existing = qs("#js-notification");
    if (existing) existing.remove();

    var bgClass = "bg-blue-500";
    if (type === "error") bgClass = "bg-red-500";
    else if (type === "success") bgClass = "bg-green-500";
    else if (type === "warning") bgClass = "bg-yellow-500";

    var textClass = type === "warning" ? "text-gray-900" : "text-white";

    var notification = createElement(
      "div",
      {
        id: "js-notification",
        className:
          "fixed top-4 right-4 z-50 px-4 py-3 rounded-lg shadow-lg " +
          bgClass +
          " " +
          textClass +
          " text-sm font-medium transition-opacity duration-300 max-w-sm",
      },
      [message]
    );

    document.body.appendChild(notification);

    setTimeout(function () {
      notification.style.opacity = "0";
      setTimeout(function () {
        if (notification.parentNode) {
          notification.remove();
        }
      }, 300);
    }, 3000);
  }

  // ============================================================
  // Workout Form Submission (JSON)
  // ============================================================

  function initWorkoutFormSubmission() {
    var form = qs("#workout-form");
    if (!form) return;

    on(form, "submit", function (e) {
      var exercises = qsa("[data-exercise-index]", form);
      if (exercises.length === 0) {
        e.preventDefault();
        showNotification(
          "Please add at least one exercise to your workout.",
          "error"
        );
        return;
      }

      var hasEmptyExercise = false;
      exercises.forEach(function (exEl) {
        var select = qs(".exercise-select", exEl);
        if (select && !select.value) {
          hasEmptyExercise = true;
        }
        var sets = qsa("[data-set-row]", exEl);
        if (sets.length === 0) {
          hasEmptyExercise = true;
        }
      });

      if (hasEmptyExercise) {
        e.preventDefault();
        showNotification(
          "Each exercise must be selected and have at least one set.",
          "error"
        );
        return;
      }
    });
  }

  // ============================================================
  // Template Form: Exercise & Set Management
  // ============================================================

  function initTemplateForm() {
    var container = qs("#template-exercises-container");
    var addBtn = qs("#add-template-exercise-btn");

    if (!container || !addBtn) return;

    exerciseIndex = getNextExerciseIndexFromContainer(container);

    on(addBtn, "click", function (e) {
      e.preventDefault();
      addTemplateExerciseRow(container);
    });

    delegate(container, "click", ".remove-exercise-btn", function (e, btn) {
      e.preventDefault();
      var row = btn.closest("[data-exercise-index]");
      if (row) {
        row.remove();
        renumberTemplateExercises(container);
      }
    });
  }

  function getNextExerciseIndexFromContainer(container) {
    var existing = qsa("[data-exercise-index]", container);
    var maxIdx = -1;
    existing.forEach(function (el) {
      var idx = parseInt(el.getAttribute("data-exercise-index"), 10);
      if (idx > maxIdx) maxIdx = idx;
    });
    return maxIdx + 1;
  }

  function addTemplateExerciseRow(container, data) {
    var idx = exerciseIndex++;
    var sortOrder = qsa("[data-exercise-index]", container).length + 1;
    var exerciseOptions = getExerciseOptionsHTML();

    var selectedId = data && data.exercise_id ? data.exercise_id : "";
    var defaultSets = data && data.default_sets ? data.default_sets : 3;
    var defaultReps = data && data.default_reps ? data.default_reps : "";
    var defaultWeight = data && data.default_weight ? data.default_weight : "";

    var html =
      '<div class="bg-white border border-gray-200 rounded-lg p-4 mb-4" data-exercise-index="' +
      idx +
      '">' +
      '  <div class="flex items-center justify-between mb-3">' +
      '    <h4 class="text-lg font-semibold text-gray-700">Exercise <span class="exercise-number">' +
      sortOrder +
      "</span></h4>" +
      '    <button type="button" class="remove-exercise-btn text-red-500 hover:text-red-700 p-2 min-w-[44px] min-h-[44px] flex items-center justify-center" title="Remove exercise">' +
      '      <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>' +
      "    </button>" +
      "  </div>" +
      '  <input type="hidden" name="exercises[' +
      idx +
      '][sort_order]" value="' +
      sortOrder +
      '" class="sort-order-input">' +
      '  <div class="mb-3">' +
      '    <label class="block text-sm font-medium text-gray-700 mb-1">Exercise</label>' +
      '    <select name="exercises[' +
      idx +
      '][exercise_id]" class="exercise-select w-full border border-gray-300 rounded-md px-3 py-2 min-h-[44px]" required>' +
      '      <option value="">Select an exercise</option>' +
      exerciseOptions +
      "    </select>" +
      "  </div>" +
      '  <div class="grid grid-cols-3 gap-2">' +
      '    <div>' +
      '      <label class="block text-sm font-medium text-gray-700 mb-1">Sets</label>' +
      '      <input type="number" name="exercises[' +
      idx +
      '][default_sets]" value="' +
      defaultSets +
      '" min="1" class="w-full border border-gray-300 rounded px-2 py-1 min-h-[44px]">' +
      "    </div>" +
      '    <div>' +
      '      <label class="block text-sm font-medium text-gray-700 mb-1">Reps</label>' +
      '      <input type="number" name="exercises[' +
      idx +
      '][default_reps]" value="' +
      defaultReps +
      '" min="1" class="w-full border border-gray-300 rounded px-2 py-1 min-h-[44px]" placeholder="Reps">' +
      "    </div>" +
      '    <div>' +
      '      <label class="block text-sm font-medium text-gray-700 mb-1">Weight</label>' +
      '      <input type="number" name="exercises[' +
      idx +
      '][default_weight]" value="' +
      defaultWeight +
      '" min="0" step="0.5" class="w-full border border-gray-300 rounded px-2 py-1 min-h-[44px]" placeholder="kg">' +
      "    </div>" +
      "  </div>" +
      "</div>";

    var wrapper = createElement("div", { innerHTML: html });
    var el = wrapper.firstElementChild;
    container.appendChild(el);

    if (selectedId) {
      var select = qs(".exercise-select", el);
      if (select) select.value = selectedId;
    }

    return el;
  }

  function renumberTemplateExercises(container) {
    var exercises = qsa("[data-exercise-index]", container);
    exercises.forEach(function (el, i) {
      var numberSpan = qs(".exercise-number", el);
      if (numberSpan) numberSpan.textContent = i + 1;
      var sortInput = qs(".sort-order-input", el);
      if (sortInput) sortInput.value = i + 1;
    });
  }

  // ============================================================
  // Flash Message Auto-Dismiss
  // ============================================================

  function initFlashDismiss() {
    var flashMessages = qsa("[data-flash-dismiss]");
    flashMessages.forEach(function (el) {
      var delay = parseInt(el.getAttribute("data-flash-dismiss"), 10) || 5000;
      setTimeout(function () {
        el.style.transition = "opacity 0.3s ease";
        el.style.opacity = "0";
        setTimeout(function () {
          if (el.parentNode) el.remove();
        }, 300);
      }, delay);

      var closeBtn = qs("[data-dismiss-btn]", el);
      if (closeBtn) {
        on(closeBtn, "click", function (e) {
          e.preventDefault();
          el.style.transition = "opacity 0.3s ease";
          el.style.opacity = "0";
          setTimeout(function () {
            if (el.parentNode) el.remove();
          }, 300);
        });
      }
    });
  }

  // ============================================================
  // Measurement Form: Date Uniqueness Warning
  // ============================================================

  function initMeasurementForm() {
    var dateInput = qs('input[name="measurement_date"]');
    if (!dateInput) return;

    var existingDates = window.__existingMeasurementDates || [];

    on(dateInput, "change", function () {
      var val = dateInput.value;
      var warning = qs("#date-warning");
      if (existingDates.indexOf(val) !== -1) {
        if (!warning) {
          var w = createElement("p", {
            id: "date-warning",
            className: "text-yellow-600 text-sm mt-1",
            textContent:
              "You already have a measurement for this date. Saving will update the existing entry.",
          });
          dateInput.parentNode.appendChild(w);
        }
      } else {
        if (warning) warning.remove();
      }
    });
  }

  // ============================================================
  // Duration Timer (optional workout timer)
  // ============================================================

  function initWorkoutTimer() {
    var timerDisplay = qs("#workout-timer");
    var startBtn = qs("#timer-start");
    var stopBtn = qs("#timer-stop");
    var durationInput = qs('input[name="duration_minutes"]');

    if (!timerDisplay || !startBtn) return;

    var startTime = null;
    var timerInterval = null;

    on(startBtn, "click", function (e) {
      e.preventDefault();
      startTime = Date.now();
      startBtn.classList.add("hidden");
      if (stopBtn) stopBtn.classList.remove("hidden");

      timerInterval = setInterval(function () {
        var elapsed = Math.floor((Date.now() - startTime) / 1000);
        var minutes = Math.floor(elapsed / 60);
        var seconds = elapsed % 60;
        timerDisplay.textContent =
          String(minutes).padStart(2, "0") +
          ":" +
          String(seconds).padStart(2, "0");
      }, 1000);
    });

    if (stopBtn) {
      on(stopBtn, "click", function (e) {
        e.preventDefault();
        if (timerInterval) {
          clearInterval(timerInterval);
          timerInterval = null;
        }
        if (startTime && durationInput) {
          var elapsed = Math.floor((Date.now() - startTime) / 60000);
          durationInput.value = Math.max(1, elapsed);
        }
        stopBtn.classList.add("hidden");
        startBtn.classList.remove("hidden");
      });
    }
  }

  // ============================================================
  // Initialize Everything on DOMContentLoaded
  // ============================================================

  function init() {
    initMobileMenu();
    initDeleteConfirmations();
    initFormValidation();
    initWorkoutForm();
    initWorkoutFormSubmission();
    initTemplateSelector();
    initTemplateForm();
    initFlashDismiss();
    initMeasurementForm();
    initWorkoutTimer();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  // Expose helpers for inline use if needed
  window.FitLog = {
    showNotification: showNotification,
    addExerciseRow: addExerciseRow,
    addSetRow: addSetRow,
  };
})();