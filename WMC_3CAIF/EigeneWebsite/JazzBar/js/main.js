document.addEventListener("DOMContentLoaded", () => {
  // nav
  const nav = document.querySelector("nav");
  const navLinks = document.querySelector("nav ul");
  const burgerBtn = document.getElementById("burgerBtn");
  const mobileMenu = document.getElementById("mobileMenu");

  if (burgerBtn) {
    burgerBtn.addEventListener("click", () => {
      mobileMenu.classList.toggle("hidden");
      mobileMenu.classList.toggle("flex");
      nav.classList.toggle("overflow-visible");
    });
  }

  // audio
  const audio = document.getElementById("backgroundJazz");
  const musicBtn = document.getElementById("musicToggle");
  const musicIcon = musicBtn.querySelector("svg");

  const STORAGE_KEY_MUTED = "theLighthouse_isMuted";
  const STORAGE_KEY_TIME = "theLighthouse_currentTime";
  const STORAGE_KEY_TIMESTAMP = "theLighthouse_timestamp";

  // icon die wir brauchen
  const speakerIcon = `
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
    `;
  const muteIcon = `
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2" />
    `;

  // video pts katze pts katze
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

    // checkt ob video läuft (beatboxen)
    promoVideo
      .play()
      .catch((e) => console.log("Promo video autoplay blocked", e));
  }

  // lade gespeicherte einstellungen
  let isMuted = localStorage.getItem(STORAGE_KEY_MUTED) === "true";
  let savedTime = parseFloat(localStorage.getItem(STORAGE_KEY_TIME));
  let savedTimestamp = parseInt(localStorage.getItem(STORAGE_KEY_TIMESTAMP));

  // checkt vergangene zeit auf der seite
  if (!isNaN(savedTime) && !isNaN(savedTimestamp)) {
    audio.currentTime = savedTime;
  }

  // mute button label
  const musicLabel = document.createElement("span");
  musicLabel.className =
    "absolute right-full mr-3 top-1/2 -translate-y-1/2 whitespace-nowrap bg-brown-dark/80 text-gold px-3 py-1 rounded-md text-xs uppercase tracking-widest opacity-100 transition-opacity duration-1000 pointer-events-none";
  musicLabel.innerText = "Sound";
  musicBtn.parentElement.appendChild(musicLabel);

  // fade out label
  setTimeout(() => {
    musicLabel.classList.remove("opacity-100");
    musicLabel.classList.add("opacity-0");
  }, 5000);

  // label zeigen on hover
  musicBtn.parentElement.classList.add("group");
  musicBtn.addEventListener("mouseenter", () => {
    musicLabel.classList.remove("opacity-0");
    musicLabel.classList.add("opacity-100");
  });
  musicBtn.addEventListener("mouseleave", () => {
    musicLabel.classList.remove("opacity-100");
    musicLabel.classList.add("opacity-0");
  });

  // volume auf 1%
  audio.volume = 0.1;
  audio.muted = isMuted;
  promoVideo.volume = 0.4;
  updateIcon();

  // audio autoplay nen try geben (es geht nicht :( )
  const playAudio = async () => {
    try {
      await audio.play();
      console.log("Audio playing successfully");
    } catch (err) {
      console.log("Autoplay blocked. Fallback to Muted Autoplay.");
      // wenns nicht geht spielst aber is muted
      audio.muted = true;
      isMuted = true;
      updateIcon();

      // label "click to unmute"
      musicLabel.innerText = "Click to Unmute";
      musicLabel.classList.remove("opacity-0");
      musicLabel.classList.add("opacity-100");
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

  // mute button handler
  musicBtn.addEventListener("click", () => {
    if (audio.muted) {
      // unmute
      audio.muted = false;
      // checkt obs läuft
      if (audio.paused) {
        audio.play();
      }
    } else {
      // mute
      audio.muted = true;
    }

    isMuted = audio.muted;
    updateIcon();
    localStorage.setItem(STORAGE_KEY_MUTED, isMuted);
  });

  // zeit speichern on unload
  window.addEventListener("beforeunload", () => {
    localStorage.setItem(STORAGE_KEY_TIME, audio.currentTime);
    localStorage.setItem(STORAGE_KEY_TIMESTAMP, Date.now());
  });

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
