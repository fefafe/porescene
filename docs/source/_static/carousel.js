document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".ps-carousel").forEach(initCarousel);
});

function initCarousel(root) {
    const slides = Array.from(root.querySelectorAll(".ps-carousel-slide"));
    const dotsContainer = root.querySelector(".ps-carousel-dots");
    const prevBtn = root.querySelector(".ps-carousel-prev");
    const nextBtn = root.querySelector(".ps-carousel-next");
    if (slides.length === 0) return;

    let index = Math.max(
        slides.findIndex((slide) => slide.classList.contains("is-active")),
        0
    );

    const dots = slides.map((_, i) => {
        const dot = document.createElement("button");
        dot.type = "button";
        dot.className = "ps-carousel-dot";
        dot.setAttribute("aria-label", `Go to slide ${i + 1}`);
        dot.addEventListener("click", () => goTo(i));
        dotsContainer.appendChild(dot);
        return dot;
    });

    function goTo(i) {
        slides[index].classList.remove("is-active");
        dots[index].classList.remove("is-active");
        index = (i + slides.length) % slides.length;
        slides[index].classList.add("is-active");
        dots[index].classList.add("is-active");
    }

    prevBtn?.addEventListener("click", () => goTo(index - 1));
    nextBtn?.addEventListener("click", () => goTo(index + 1));
    goTo(index);

    const intervalMs = Number(root.dataset.interval) || 5000;
    let timer = setInterval(() => goTo(index + 1), intervalMs);
    const stop = () => clearInterval(timer);
    const resume = () => {
        stop();
        timer = setInterval(() => goTo(index + 1), intervalMs);
    };
    root.addEventListener("mouseenter", stop);
    root.addEventListener("mouseleave", resume);
    root.addEventListener("focusin", stop);
    root.addEventListener("focusout", resume);

    root.setAttribute("tabindex", "0");
    root.addEventListener("keydown", (e) => {
        if (e.key === "ArrowLeft") goTo(index - 1);
        if (e.key === "ArrowRight") goTo(index + 1);
    });
}
