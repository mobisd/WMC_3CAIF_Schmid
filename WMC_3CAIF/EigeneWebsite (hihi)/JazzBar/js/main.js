document.addEventListener("DOMContentLoaded", () => {
  // --- Navbar Logic ---
  const nav = document.querySelector("nav");
  const navLinks = document.querySelector("nav ul"); // Desktop links
  const burgerBtn = document.getElementById("burgerBtn");
  const mobileMenu = document.getElementById("mobileMenu");
  let isHovering = false;

  // Scroll Detection
  window.addEventListener("scroll", () => {
    if (window.scrollY > 50) {
      // Only collapse if we are NOT hovering
      if (!isHovering && !mobileMenu.classList.contains("flex")) {
        nav.classList.add("nav-collapsed");
        nav.classList.remove("nav-expanded");
      }
    } else {
      // At top, always expanded
      nav.classList.remove("nav-collapsed");
      nav.classList.remove("nav-expanded");
    }
  });

  // Hover Logic for Desktop
  const logo = nav.querySelector("a:first-child");

  // Expand when hovering over the collapsed nav (or specifically the logo area)
  nav.addEventListener("mouseenter", () => {
    isHovering = true;
    if (window.scrollY > 50) {
      nav.classList.remove("nav-collapsed");
      nav.classList.add("nav-expanded");
    }
  });

  nav.addEventListener("mouseleave", () => {
    isHovering = false;
    if (window.scrollY > 50 && !mobileMenu.classList.contains("flex")) {
      nav.classList.remove("nav-expanded");
      nav.classList.add("nav-collapsed");
    }
  });

  // Mobile Menu Toggle
  if (burgerBtn) {
    burgerBtn.addEventListener("click", () => {
      mobileMenu.classList.toggle("hidden");
      mobileMenu.classList.toggle("flex");
    });
  }

  // --- Audio Logic with Persistence ---
  const audio = document.getElementById("backgroundJazz");
  const musicBtn = document.getElementById("musicToggle");
  const musicIcon = musicBtn.querySelector("svg");

  // Keys for localStorage
  const STORAGE_KEY_MUTED = "theLighthouse_isMuted";
  const STORAGE_KEY_TIME = "theLighthouse_currentTime";
  const STORAGE_KEY_TIMESTAMP = "theLighthouse_timestamp";

  // Icons
  const speakerIcon = `
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
    `;
  const muteIcon = `
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2" />
    `;

  // --- Promo Video Logic ---
  const promoVideo = document.getElementById("promoVideo");
  const promoBtn = document.getElementById("promoMuteBtn");

  if (promoVideo && promoBtn) {
    const promoIcon = promoBtn.querySelector("svg");

    promoBtn.addEventListener("click", () => {
      if (promoVideo.muted) {
        promoVideo.muted = false;
        promoIcon.innerHTML = speakerIcon;
      } else {
        promoVideo.muted = true;
        promoIcon.innerHTML = muteIcon;
      }
    });

    // Ensure it plays
    promoVideo
      .play()
      .catch((e) => console.log("Promo video autoplay blocked", e));
  }

  // 1. Initialize State
  let isMuted = localStorage.getItem(STORAGE_KEY_MUTED) === "true";
  let savedTime = parseFloat(localStorage.getItem(STORAGE_KEY_TIME));
  let savedTimestamp = parseInt(localStorage.getItem(STORAGE_KEY_TIMESTAMP));

  // Calculate elapsed time if moving between pages
  // (Optional: simply resuming from savedTime is often enough, but adding elapsed time makes it feel like a continuous stream)
  if (!isNaN(savedTime) && !isNaN(savedTimestamp)) {
    // Just resume from saved time for simplicity to avoid running past duration
    audio.currentTime = savedTime;
  }

  // Create Label for Mute Button
  const musicLabel = document.createElement("span");
  musicLabel.className =
    "absolute right-full mr-3 top-1/2 -translate-y-1/2 whitespace-nowrap bg-brown-dark/80 text-gold px-3 py-1 rounded-md text-xs uppercase tracking-widest opacity-100 transition-opacity duration-1000 pointer-events-none";
  musicLabel.innerText = "Sound";
  musicBtn.parentElement.appendChild(musicLabel);

  // Fade out label after 5 seconds
  setTimeout(() => {
    musicLabel.classList.remove("opacity-100");
    musicLabel.classList.add("opacity-0");
  }, 5000);

  // Show label on hover
  musicBtn.parentElement.classList.add("group");
  musicBtn.addEventListener("mouseenter", () => {
    musicLabel.classList.remove("opacity-0");
    musicLabel.classList.add("opacity-100");
  });
  musicBtn.addEventListener("mouseleave", () => {
    musicLabel.classList.remove("opacity-100");
    musicLabel.classList.add("opacity-0");
  });

  // Apply Volume & Mute State
  audio.volume = 0.01;
  audio.muted = isMuted;
  updateIcon();

  // 2. Robust Autoplay Attempt
  const playAudio = async () => {
    try {
      await audio.play();
      console.log("Audio playing successfully");
    } catch (err) {
      console.log("Autoplay blocked. Fallback to Muted Autoplay.");
      // Fallback: Mute and play
      audio.muted = true;
      isMuted = true;
      updateIcon();

      // Notify user they need to unmute
      musicLabel.innerText = "Click to Unmute";
      musicLabel.classList.remove("opacity-0");
      musicLabel.classList.add("opacity-100");
      // Hide again after a delay
      setTimeout(() => {
        musicLabel.innerText = "Sound";
        musicLabel.classList.remove("opacity-100");
        musicLabel.classList.add("opacity-0");
      }, 8000);

      try {
        await audio.play();
        console.log("Audio playing muted (fallback)");
      } catch (err2) {
        console.log("Even muted autoplay failed (unlikely)");
      }
    }
  };

  playAudio();

  // 3. Toggle Button Handler
  musicBtn.addEventListener("click", () => {
    if (audio.muted) {
      // Unmute
      audio.muted = false;
      // Ensure it's playing (in case autoplay was blocked)
      if (audio.paused) {
        audio.play();
      }
    } else {
      // Mute
      audio.muted = true;
    }

    isMuted = audio.muted;
    updateIcon();
    localStorage.setItem(STORAGE_KEY_MUTED, isMuted);
  });

  // 4. Save Time on Unload
  window.addEventListener("beforeunload", () => {
    localStorage.setItem(STORAGE_KEY_TIME, audio.currentTime);
    localStorage.setItem(STORAGE_KEY_TIMESTAMP, Date.now());
  });

  // Helper to update UI
  // Helper to update UI
  function updateIcon() {
    if (isMuted) {
      musicIcon.innerHTML = muteIcon;
      musicBtn.classList.add("bg-gray-400");
      musicBtn.classList.remove("bg-gold");
    } else {
      musicIcon.innerHTML = speakerIcon;
      musicBtn.classList.remove("bg-gray-400");
      musicBtn.classList.add("bg-gold");
    }
  }
});
