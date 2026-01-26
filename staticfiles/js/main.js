/* ===============================
   NAVBAR SCROLL EFFECT
================================ */
window.addEventListener("scroll", () => {
    const navbar = document.querySelector(".navbar");
    if (!navbar) return;

    if (window.scrollY > 50) {
        navbar.classList.add("scrolled");
    } else {
        navbar.classList.remove("scrolled");
    }
});

/* ===============================
   INTERSECTION OBSERVER
   Fade + Slide Animation
================================ */
const observer = new IntersectionObserver(
    entries => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add("show");
            }
        });
    },
    { threshold: 0.2 }
);

document.querySelectorAll(".fade-slide").forEach(el => {
    observer.observe(el);
});
document.querySelectorAll("i").forEach(icon => {
    icon.addEventListener("mouseenter", () => {
        icon.style.filter = "drop-shadow(0 0 8px #6366f1)";
    });

    icon.addEventListener("mouseleave", () => {
        icon.style.filter = "none";
    });
});
