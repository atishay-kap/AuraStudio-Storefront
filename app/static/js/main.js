/**
 * AURA STUDIO — Haute Couture Frontend Engine (Faith Ibiza Inspired)
 * Fullscreen Cover Parallax, Silky 120fps Scroll Reveal Engine, Dynamic Header & Micro-Animations.
 */

document.addEventListener("DOMContentLoaded", () => {
    // -------------------------------------------------------------
    // 1. Fullscreen Hero Parallax & Scroll Progress
    // -------------------------------------------------------------
    const progressBar = document.getElementById("scroll-progress-bar");
    const categoryNav = document.getElementById("category-nav");
    const heroBg = document.getElementById("hero-parallax-bg");

    let ticking = false;

    function handleScrollUpdates() {
        const currentScrollY = window.scrollY;
        const totalHeight = document.documentElement.scrollHeight - window.innerHeight;

        // Progress bar calculation
        if (progressBar && totalHeight > 0) {
            const progress = (currentScrollY / totalHeight) * 100;
            progressBar.style.width = `${Math.min(100, Math.max(0, progress))}%`;
        }

        // Sticky category nav shadow intensification
        if (categoryNav) {
            if (currentScrollY > 40) {
                categoryNav.classList.add("is-stuck");
            } else {
                categoryNav.classList.remove("is-stuck");
            }
        }

        // Parallax background drift on full-screen cover hero
        if (heroBg) {
            const parallaxOffset = currentScrollY * 0.28;
            heroBg.style.transform = `scale(1.05) translate3d(0, ${parallaxOffset}px, 0)`;
        }

        ticking = false;
    }

    window.addEventListener("scroll", () => {
        if (!ticking) {
            window.requestAnimationFrame(handleScrollUpdates);
            ticking = true;
        }
    }, { passive: true });

    // Initial check on load
    handleScrollUpdates();

    // -------------------------------------------------------------
    // 3. Faith Ibiza Style Intersection Observer Scroll Reveals
    // -------------------------------------------------------------
    const revealElements = document.querySelectorAll(".reveal-on-scroll, [data-reveal]");
    
    if ("IntersectionObserver" in window && revealElements.length > 0) {
        const revealObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add("is-revealed");
                    observer.unobserve(entry.target);
                }
            });
        }, {
            root: null,
            threshold: 0.06,
            rootMargin: "0px 0px -30px 0px"
        });

        revealElements.forEach(el => revealObserver.observe(el));
    } else {
        revealElements.forEach(el => el.classList.add("is-revealed"));
    }

    // Auto-stagger delay for grid items
    const staggerGroups = document.querySelectorAll(".reveal-stagger-group");
    staggerGroups.forEach(group => {
        const children = group.querySelectorAll(".reveal-stagger-item, .product-card-fast");
        children.forEach((child, index) => {
            child.style.setProperty("--stagger-index", index % 8);
        });
    });

    // -------------------------------------------------------------
    // 4. File Upload Drag-and-Drop & Instant Live Image Preview
    // -------------------------------------------------------------
    const fileInputs = document.querySelectorAll('input[type="file"][data-preview-target]');
    fileInputs.forEach(input => {
        const targetId = input.getAttribute("data-preview-target");
        const previewImg = document.getElementById(targetId);
        const dropZone = input.closest(".dropzone-box");

        function handleFile(file) {
            if (!file || !file.type.startsWith("image/")) return;
            const reader = new FileReader();
            reader.onload = (e) => {
                if (previewImg) {
                    previewImg.src = e.target.result;
                    previewImg.style.display = "block";
                    const placeholder = previewImg.parentElement.querySelector(".preview-placeholder");
                    if (placeholder) placeholder.style.display = "none";
                }
            };
            reader.readAsDataURL(file);
        }

        input.addEventListener("change", (e) => {
            if (e.target.files && e.target.files[0]) {
                handleFile(e.target.files[0]);
            }
        });

        if (dropZone) {
            ["dragenter", "dragover"].forEach(eventName => {
                dropZone.addEventListener(eventName, (e) => {
                    e.preventDefault();
                    dropZone.classList.add("dragover");
                }, false);
            });

            ["dragleave", "drop"].forEach(eventName => {
                dropZone.addEventListener(eventName, (e) => {
                    e.preventDefault();
                    dropZone.classList.remove("dragover");
                }, false);
            });

            dropZone.addEventListener("drop", (e) => {
                const dt = e.dataTransfer;
                const files = dt.files;
                if (files && files.length > 0) {
                    input.files = files;
                    handleFile(files[0]);
                }
            });
        }
    });

    // -------------------------------------------------------------
    // 5. Wishlist Interactive Heart Pulse Micro-Animation
    // -------------------------------------------------------------
    const wishlistButtons = document.querySelectorAll(".btn-wishlist-float, .btn-wishlist-toggle, .wishlist-btn-fast, .wishlist-btn-detail");
    wishlistButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            btn.classList.add("heart-pulse");
            setTimeout(() => btn.classList.remove("heart-pulse"), 450);
        }, { passive: true });
    });

    // -------------------------------------------------------------
    // 6. Interactive Star Rating in Reviews
    // -------------------------------------------------------------
    const ratingSelect = document.getElementById("rating-select");
    const starContainer = document.getElementById("interactive-star-rating");
    const ratingLabel = document.getElementById("star-rating-text");
    
    const RATING_DESCRIPTIONS = {
        5: "5 Stars — Outstanding Luxury & Drape (★ ★ ★ ★ ★)",
        4: "4 Stars — Great Quality & Fit (★ ★ ★ ★ ☆)",
        3: "3 Stars — Average Quality (★ ★ ★ ☆ ☆)",
        2: "2 Stars — Below Expectations (★ ★ ☆ ☆ ☆)",
        1: "1 Star — Poor Quality (★ ☆ ☆ ☆ ☆)"
    };

    if (starContainer && ratingSelect) {
        const stars = starContainer.querySelectorAll(".star-choice");
        
        function highlightStars(val) {
            stars.forEach(s => {
                const v = parseInt(s.getAttribute("data-value"), 10);
                s.classList.toggle("hovered", v <= val);
            });
            if (ratingLabel && RATING_DESCRIPTIONS[val]) {
                ratingLabel.textContent = RATING_DESCRIPTIONS[val];
            }
        }

        function setActiveStars(val) {
            stars.forEach(s => {
                const v = parseInt(s.getAttribute("data-value"), 10);
                s.classList.toggle("active", v <= val);
                s.classList.remove("hovered");
            });
            if (ratingLabel && RATING_DESCRIPTIONS[val]) {
                ratingLabel.textContent = RATING_DESCRIPTIONS[val];
            }
        }

        stars.forEach(star => {
            star.addEventListener("mouseenter", () => {
                const val = parseInt(star.getAttribute("data-value"), 10);
                highlightStars(val);
            }, { passive: true });
            star.addEventListener("click", () => {
                const val = parseInt(star.getAttribute("data-value"), 10);
                ratingSelect.value = val;
                setActiveStars(val);
            });
        });

        starContainer.addEventListener("mouseleave", () => {
            const currentVal = parseInt(ratingSelect.value, 10) || 5;
            setActiveStars(currentVal);
        }, { passive: true });

        const initialVal = parseInt(ratingSelect.value, 10) || 5;
        setActiveStars(initialVal);
    }

    // -------------------------------------------------------------
    // 7. Auto-Dismiss Flash Messages
    // -------------------------------------------------------------
    const flashMessages = document.querySelectorAll(".flashes li");
    flashMessages.forEach((msg, idx) => {
        setTimeout(() => {
            msg.style.transition = "opacity 0.6s cubic-bezier(0.16, 1, 0.3, 1), transform 0.6s cubic-bezier(0.16, 1, 0.3, 1)";
            msg.style.opacity = "0";
            msg.style.transform = "translate3d(0, -12px, 0)";
            setTimeout(() => msg.remove(), 620);
        }, 4500 + idx * 600);
    });

    // -------------------------------------------------------------
    // 8. Global Luxury Quantity Stepper Handler
    // -------------------------------------------------------------
    window.stepDetailQty = function(delta) {
        const input = document.getElementById("qty");
        if (!input) return;
        const min = parseInt(input.min, 10) || 1;
        const max = parseInt(input.max, 10) || 999;
        let current = parseInt(input.value, 10) || 1;
        current += delta;
        if (current < min) current = min;
        if (current > max) current = max;
        input.value = current;
    };

    // -------------------------------------------------------------
    // 9. Interactive Atelier Size Selector Handler
    // -------------------------------------------------------------
    window.selectProductSize = function(size, btnElement) {
        const hiddenInput = document.getElementById("selected-size-input");
        if (hiddenInput) {
            hiddenInput.value = size;
        }
        const container = btnElement ? btnElement.closest(".size-chips-grid") : document.querySelector(".size-chips-grid");
        if (container) {
            container.querySelectorAll(".size-chip-btn").forEach(btn => btn.classList.remove("active"));
        }
        if (btnElement) {
            btnElement.classList.add("active");
        }
    };
});
