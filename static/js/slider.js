/* ===============================
   TESTIMONIAL AUTO SLIDER
================================ */
const slides = document.querySelectorAll(".testimonial-card");
let index = 0;

function showSlide(i) {
    slides.forEach((slide, idx) => {
        slide.classList.toggle("active", idx === i);
    });
}

function autoSlide() {
    index = (index + 1) % slides.length;
    showSlide(index);
}

if (slides.length > 0) {
    showSlide(index);
    setInterval(autoSlide, 4000);
}
