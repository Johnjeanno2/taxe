/**
 * Design Ultra-Moderne pour les Formulaires Django Admin
 * Micro-interactions et animations avancées
 */

(function($) {
    'use strict';

    // Attendre que le DOM soit prêt
    $(document).ready(function() {
        // Vérifier si on est sur une page de formulaire
        if (!$('body').hasClass('grp-change-form')) {
            return;
        }

        // Initialiser toutes les fonctionnalités
        initFormProgress();
        initFloatingLabels();
        initRealTimeValidation();
        initRippleEffect();
        initAutoSave();
        initParallaxEffect();
        initFormEnhancements();
    });

    /**
     * Barre de progression du formulaire
     */
    function initFormProgress() {
        const form = document.querySelector('form');
        if (!form) return;

        let progressBar = document.querySelector('.form-progress');
        if (!progressBar) {
            progressBar = document.createElement('div');
            progressBar.className = 'form-progress';
            document.body.appendChild(progressBar);
        }

        function updateProgress() {
            const inputs = form.querySelectorAll('input:not([type="hidden"]):not([type="submit"]), select, textarea');
            const filledInputs = Array.from(inputs).filter(input => {
                if (input.type === 'checkbox' || input.type === 'radio') {
                    return input.checked;
                }
                return input.value.trim() !== '';
            });

            const progress = inputs.length > 0 ? (filledInputs.length / inputs.length) : 0;
            progressBar.style.transform = `scaleX(${progress})`;
        }

        // Mettre à jour la progression lors des changements
        $(form).on('input change', 'input, select, textarea', updateProgress);
        updateProgress(); // Initial
    }

    /**
     * Effet de floating labels
     */
    function initFloatingLabels() {
        $('.grp-module input, .grp-module select, .grp-module textarea').each(function() {
            const $input = $(this);
            const $label = $input.closest('.form-row, .grp-row').find('label');

            if ($label.length && !$label.hasClass('floating-processed')) {
                $label.addClass('floating-processed');

                function checkValue() {
                    if ($input.val() && $input.val().trim() !== '') {
                        $label.addClass('floating-active');
                    } else {
                        $label.removeClass('floating-active');
                    }
                }

                checkValue();
                $input.on('input change blur focus', checkValue);
            }
        });
    }

    /**
     * Validation en temps réel avec animations
     */
    function initRealTimeValidation() {
        $('.grp-module input[required], .grp-module select[required], .grp-module textarea[required]').each(function() {
            const $input = $(this);

            $input.on('blur', function() {
                const $row = $input.closest('.form-row, .grp-row');

                if (this.checkValidity()) {
                    $row.removeClass('error-state').addClass('success-state');
                    updateValidationIcon($row, 'success', '✓');
                } else {
                    $row.removeClass('success-state').addClass('error-state');
                    updateValidationIcon($row, 'error', '✗');
                }
            });

            $input.on('input', function() {
                const $row = $input.closest('.form-row, .grp-row');
                $row.removeClass('error-state success-state');
                $row.find('.validation-icon').remove();
            });
        });

        function updateValidationIcon($row, type, icon) {
            let $icon = $row.find('.validation-icon');
            if (!$icon.length) {
                $icon = $('<span class="validation-icon"></span>');
                $row.append($icon);
            }
            $icon.removeClass('success error').addClass(type).text(icon);
        }
    }

    /**
     * Effet ripple sur les boutons
     */
    function initRippleEffect() {
        $(document).on('click', '.grp-button, .button, input[type="submit"]', function(e) {
            const $button = $(this);
            const rect = this.getBoundingClientRect();
            const ripple = $('<span class="ripple"></span>');

            const size = Math.max(rect.width, rect.height);
            const x = e.clientX - rect.left - size / 2;
            const y = e.clientY - rect.top - size / 2;

            ripple.css({
                width: size,
                height: size,
                left: x,
                top: y
            });

            $button.css('position', 'relative').css('overflow', 'hidden');
            $button.append(ripple);

            setTimeout(() => {
                ripple.remove();
            }, 600);
        });
    }

    /**
     * Auto-save avec indicateur visuel
     */
    function initAutoSave() {
        let autoSaveTimeout;
        let $indicator;

        function showSaveIndicator(message, type) {
            if (!$indicator) {
                $indicator = $('<div class="auto-save-indicator"></div>');
                $('body').append($indicator);
            }

            $indicator.removeClass('saving saved').addClass(type).text(message);

            if (type === 'saved') {
                setTimeout(() => {
                    $indicator.removeClass('saved');
                }, 2000);
            }
        }

        $('.grp-module input, .grp-module select, .grp-module textarea').on('input change', function() {
            clearTimeout(autoSaveTimeout);

            showSaveIndicator('💾 Sauvegarde en cours...', 'saving');

            autoSaveTimeout = setTimeout(() => {
                // Simuler la sauvegarde (ici vous pourriez faire un appel AJAX)
                showSaveIndicator('✅ Sauvegardé', 'saved');
            }, 1500);
        });
    }

    /**
     * Effet de parallax subtil
     */
    function initParallaxEffect() {
        let ticking = false;

        function updateParallax() {
            const scrolled = window.pageYOffset;
            $('.grp-module').each(function(index) {
                const rate = scrolled * -0.02;
                $(this).css('transform', `translateY(${rate * (index + 1)}px)`);
            });
            ticking = false;
        }

        $(window).on('scroll', function() {
            if (!ticking) {
                requestAnimationFrame(updateParallax);
                ticking = true;
            }
        });
    }

    /**
     * Améliorations supplémentaires du formulaire
     */
    function initFormEnhancements() {
        // Animation d'entrée échelonnée pour les modules
        $('.grp-module').each(function(index) {
            $(this).css('animation-delay', `${index * 0.1}s`);
        });

        // Amélioration des champs de date
        $('input[type="date"], input[type="datetime-local"]').each(function() {
            $(this).on('focus', function() {
                $(this).closest('.form-row, .grp-row').addClass('date-focused');
            }).on('blur', function() {
                $(this).closest('.form-row, .grp-row').removeClass('date-focused');
            });
        });

        // Amélioration des textarea avec auto-resize
        $('textarea').each(function() {
            const $textarea = $(this);

            function autoResize() {
                $textarea.css('height', 'auto');
                $textarea.css('height', $textarea[0].scrollHeight + 'px');
            }

            $textarea.on('input', autoResize);
            autoResize(); // Initial
        });

        // Effet de focus amélioré
        $('.grp-module input, .grp-module select, .grp-module textarea').on('focus', function() {
            $(this).closest('.grp-module').addClass('module-focused');
        }).on('blur', function() {
            $(this).closest('.grp-module').removeClass('module-focused');
        });

        // Indicateur de champs requis
        $('.grp-module input[required], .grp-module select[required], .grp-module textarea[required]').each(function() {
            const $label = $(this).closest('.form-row, .grp-row').find('label');
            if ($label.length && !$label.find('.required-indicator').length) {
                $label.append('<span class="required-indicator" style="color: #ef4444; margin-left: 4px;">*</span>');
            }
        });

        // Amélioration des boutons d'ajout/suppression
        $('.grp-add-item, .add-row').on('click', function() {
            $(this).addClass('button-clicked');
            setTimeout(() => {
                $(this).removeClass('button-clicked');
            }, 300);
        });

        // Sauvegarde automatique du brouillon dans localStorage
        const formId = $('form').attr('id') || 'admin-form';

        function saveDraft() {
            const formData = {};
            $('.grp-module input, .grp-module select, .grp-module textarea').each(function() {
                if (this.name && this.value) {
                    formData[this.name] = this.value;
                }
            });
            localStorage.setItem(`draft_${formId}`, JSON.stringify(formData));
        }

        function loadDraft() {
            const draft = localStorage.getItem(`draft_${formId}`);
            if (draft) {
                try {
                    const formData = JSON.parse(draft);
                    Object.keys(formData).forEach(name => {
                        const $field = $(`[name="${name}"]`);
                        if ($field.length && !$field.val()) {
                            $field.val(formData[name]).trigger('change');
                        }
                    });
                } catch (e) {
                    console.warn('Erreur lors du chargement du brouillon:', e);
                }
            }
        }

        // Charger le brouillon au démarrage
        loadDraft();

        // Sauvegarder le brouillon lors des changements
        $('.grp-module input, .grp-module select, .grp-module textarea').on('input change',
            debounce(saveDraft, 1000)
        );

        // Nettoyer le brouillon lors de la soumission
        $('form').on('submit', function() {
            localStorage.removeItem(`draft_${formId}`);
        });
    }

    /**
     * Fonction utilitaire de debounce
     */
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    // Styles CSS supplémentaires injectés dynamiquement
    const additionalStyles = `
        <style>
        .module-focused {
            box-shadow: var(--shadow-lg) !important;
            border-color: var(--accent-color) !important;
        }

        .date-focused {
            background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%) !important;
            border-radius: var(--radius-md) !important;
            padding: 0.5rem !important;
            margin: -0.5rem !important;
        }

        .button-clicked {
            transform: scale(0.95) !important;
        }

        .grp-module textarea {
            transition: height 0.2s ease !important;
        }

        .required-indicator {
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        </style>
    `;

    // Injecter les styles supplémentaires
    $('head').append(additionalStyles);

})(jQuery);