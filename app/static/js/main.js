/**
 * Storefront Luxury Experience & Interactive Motion Engine
 * High-Fashion Editorial UI Animations, Ambient Glow, 3D Tilt, & File Upload Previews
 */

document.addEventListener("DOMContentLoaded", () => {
    // 0. Dynamic Luxury Runway Top Hairline Loader Bar
    if (!document.getElementById("aura-entrance-bar")) {
        const bar = document.createElement("div");
        bar.id = "aura-entrance-bar";
        bar.className = "aura-entrance-bar";
        document.body.appendChild(bar);
        setTimeout(() => bar.remove(), 1200);
    }

    // 1. Staggered Product Cards Cascade Entrance
    const productCards = document.querySelectorAll(".product-card-fast, .product-card");
    productCards.forEach((card, index) => {
        card.style.setProperty("--card-index", index);
        card.classList.add("stagger-in");
    });

    // 2. High-Performance RAF-Throttled Mouse Spotlight on Hero
    const hero = document.querySelector(".hero-container-cinematic");
    if (hero && window.matchMedia("(pointer: fine)").matches) {
        let rafPending = false;
        let lastX = 0, lastY = 0;

        hero.addEventListener("mousemove", (e) => {
            const rect = hero.getBoundingClientRect();
            lastX = e.clientX - rect.left;
            lastY = e.clientY - rect.top;

            if (!rafPending) {
                rafPending = true;
                requestAnimationFrame(() => {
                    hero.style.setProperty("--mouse-x", `${lastX}px`);
                    hero.style.setProperty("--mouse-y", `${lastY}px`);
                    rafPending = false;
                });
            }
        }, { passive: true });
    }

    // 3. Lightweight Hardware-Accelerated 3D Tilt for Desktop
    if (window.matchMedia("(pointer: fine)").matches) {
        const tiltCards = document.querySelectorAll(".product-card-fast, .hero-image-frame");
        tiltCards.forEach(card => {
            let tiltRaf = false;
            let cardRect = null;

            card.addEventListener("mouseenter", () => {
                cardRect = card.getBoundingClientRect();
            }, { passive: true });

            card.addEventListener("mousemove", (e) => {
                if (!cardRect) cardRect = card.getBoundingClientRect();
                const x = e.clientX - cardRect.left - cardRect.width / 2;
                const y = e.clientY - cardRect.top - cardRect.height / 2;

                if (!tiltRaf) {
                    tiltRaf = true;
                    requestAnimationFrame(() => {
                        const rotateX = (-y / cardRect.height) * 4;
                        const rotateY = (x / cardRect.width) * 4;
                        card.style.transform = `perspective(800px) rotateX(${rotateX.toFixed(2)}deg) rotateY(${rotateY.toFixed(2)}deg) translate3d(0, -4px, 0)`;
                        tiltRaf = false;
                    });
                }
            }, { passive: true });

            card.addEventListener("mouseleave", () => {
                cardRect = null;
                card.style.transform = "";
            }, { passive: true });
        });
    }

    // 4. Smooth Intersection Observer for Scroll Reveals
    const revealElements = document.querySelectorAll(".reveal-on-scroll, .metric-card, .invoice-card, .review-card, .card");
    const observerOptions = {
        threshold: 0.08,
        rootMargin: "0px 0px -20px 0px"
    };

    const revealObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add("revealed");
                revealObserver.unobserve(entry.target);
            }
        });
    }, observerOptions);

    revealElements.forEach(el => {
        el.classList.add("reveal-init");
        revealObserver.observe(el);
    });

    // 4. File Upload Drag-and-Drop & Instant Live Image Preview
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

    // 5. Wishlist Interactive Heart Bounce
    const wishlistButtons = document.querySelectorAll(".btn-wishlist-float, .btn-wishlist-toggle");
    wishlistButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            btn.classList.add("heart-pulse");
            setTimeout(() => btn.classList.remove("heart-pulse"), 600);
        });
    });

    // 6. Star Rating Interactive Hover in Review Forms
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
            });
            star.addEventListener("click", () => {
                const val = parseInt(star.getAttribute("data-value"), 10);
                ratingSelect.value = val;
                setActiveStars(val);
            });
        });

        starContainer.addEventListener("mouseleave", () => {
            const currentVal = parseInt(ratingSelect.value, 10) || 5;
            setActiveStars(currentVal);
        });

        // Initialize with default 5-star state
        const initialVal = parseInt(ratingSelect.value, 10) || 5;
        setActiveStars(initialVal);
    }

    // 7. Auto-Dismiss Flash Messages with smooth fade
    const flashMessages = document.querySelectorAll(".flashes li");
    flashMessages.forEach((msg, idx) => {
        setTimeout(() => {
            msg.style.opacity = "0";
            msg.style.transform = "translateY(-10px)";
            setTimeout(() => msg.remove(), 400);
        }, 5000 + idx * 800);
    });

    // 8. Global Luxury Quantity Stepper Handler
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

    // 9. Interactive Atelier Size Selector Handler
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
