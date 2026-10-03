/**
 * Story Mode Player.
 * Designed for crisp screen-recording demonstrations.
 * Enhanced with filmstrip thumbnail dots.
 * Keyboard controls:
 *   [Space] - Play / Pause
 *   [Arrow Right / Left] - Next / Prev slide
 *   [A] - Cycle aspect ratios (16:9, 1:1, 4:5)
 *   [C] - Toggle captions overlay
 *   [H] - Hide / Show UI Chrome & cursor for clean video capture
 */

document.addEventListener('DOMContentLoaded', () => {
  const slides = Array.from(document.querySelectorAll('.story-slide'));
  const filmstripDots = Array.from(document.querySelectorAll('.filmstrip-dot'));
  const totalSlides = slides.length;
  let currentIndex = 0;
  let isPlaying = false;
  let playTimer = null;
  const slideDurationMs = 7500; // ~52 seconds total for 7 slides

  const storyFrame = document.getElementById('storyFrame');
  const progressBar = document.getElementById('storyProgressFill');
  const slideIndexDisplay = document.getElementById('slideIndexDisplay');
  const playPauseBtn = document.getElementById('playPauseBtn');
  const prevBtn = document.getElementById('prevSlideBtn');
  const nextBtn = document.getElementById('nextSlideBtn');
  const aspectBtns = document.querySelectorAll('.aspect-btn');
  const captionsElem = document.getElementById('storyCaptions');
  const navBar = document.getElementById('storyNavBar');

  const aspectRatios = ['aspect-16-9', 'aspect-1-1', 'aspect-4-5'];
  let currentAspectIndex = 0;
  let captionsVisible = true;
  let chromeVisible = true;

  function showSlide(index) {
    if (index < 0) index = 0;
    if (index >= totalSlides) index = totalSlides - 1;
    currentIndex = index;

    slides.forEach((s, idx) => {
      s.classList.toggle('active', idx === currentIndex);
    });

    filmstripDots.forEach((dot, idx) => {
      dot.classList.toggle('active', idx === currentIndex);
    });

    slideIndexDisplay.textContent = `${currentIndex + 1} / ${totalSlides}`;
    const fillPct = ((currentIndex + 1) / totalSlides) * 100;
    progressBar.style.width = `${fillPct}%`;

    // Update captions if present
    const activeSlide = slides[currentIndex];
    const captionText = activeSlide.getAttribute('data-caption') || '';
    if (captionsElem) {
      captionsElem.textContent = captionText;
      captionsElem.style.display = (captionsVisible && captionText) ? 'block' : 'none';
    }
  }

  function nextSlide() {
    if (currentIndex < totalSlides - 1) {
      showSlide(currentIndex + 1);
    } else {
      pause();
    }
  }

  function prevSlide() {
    if (currentIndex > 0) {
      showSlide(currentIndex - 1);
    }
  }

  function play() {
    isPlaying = true;
    playPauseBtn.textContent = '⏸ Pause (Space)';
    clearInterval(playTimer);
    playTimer = setInterval(() => {
      if (currentIndex < totalSlides - 1) {
        nextSlide();
      } else {
        pause();
      }
    }, slideDurationMs);
  }

  function pause() {
    isPlaying = false;
    playPauseBtn.textContent = '▶ Play (Space)';
    clearInterval(playTimer);
  }

  function togglePlay() {
    if (isPlaying) pause();
    else play();
  }

  function setAspectRatio(aspectClass) {
    aspectRatios.forEach(cls => storyFrame.classList.remove(cls));
    storyFrame.classList.add(aspectClass);
    aspectBtns.forEach(btn => {
      btn.classList.toggle('active', btn.getAttribute('data-aspect') === aspectClass);
    });
  }

  function cycleAspectRatio() {
    currentAspectIndex = (currentAspectIndex + 1) % aspectRatios.length;
    setAspectRatio(aspectRatios[currentAspectIndex]);
  }

  function toggleCaptions() {
    captionsVisible = !captionsVisible;
    showSlide(currentIndex);
  }

  function toggleChrome() {
    chromeVisible = !chromeVisible;
    navBar.style.display = chromeVisible ? 'flex' : 'none';
    document.body.style.cursor = chromeVisible ? 'default' : 'none';
  }

  // Button Listeners
  playPauseBtn.addEventListener('click', togglePlay);
  prevBtn.addEventListener('click', prevSlide);
  nextBtn.addEventListener('click', nextSlide);

  filmstripDots.forEach(dot => {
    dot.addEventListener('click', () => {
      const idx = parseInt(dot.getAttribute('data-index'), 10);
      showSlide(idx);
    });
  });

  aspectBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const cls = btn.getAttribute('data-aspect');
      setAspectRatio(cls);
    });
  });

  // Global Keyboard Navigation
  window.addEventListener('keydown', (e) => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

    if (e.code === 'Space') {
      e.preventDefault();
      togglePlay();
    } else if (e.code === 'ArrowRight') {
      e.preventDefault();
      nextSlide();
    } else if (e.code === 'ArrowLeft') {
      e.preventDefault();
      prevSlide();
    } else if (e.key.toLowerCase() === 'a') {
      e.preventDefault();
      cycleAspectRatio();
    } else if (e.key.toLowerCase() === 'c') {
      e.preventDefault();
      toggleCaptions();
    } else if (e.key.toLowerCase() === 'h') {
      e.preventDefault();
      toggleChrome();
    }
  });

  showSlide(0);
});
