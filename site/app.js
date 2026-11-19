(() => {
  const root = document.documentElement;
  root.classList.add("js");

  const nav = document.querySelector(".nav");
  const toggle = document.querySelector(".nav-toggle");
  const links = document.getElementById("nav-links");
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

  const onScroll = () => {
    if (nav) nav.classList.toggle("is-scrolled", window.scrollY > 8);
  };
  onScroll();
  window.addEventListener("scroll", onScroll, { passive: true });

  const setMenu = (open) => {
    if (!toggle || !links) return;
    toggle.setAttribute("aria-expanded", String(open));
    toggle.setAttribute("aria-label", open ? "关闭菜单" : "打开菜单");
    links.classList.toggle("is-open", open);
  };

  if (toggle && links) {
    toggle.addEventListener("click", () => {
      setMenu(toggle.getAttribute("aria-expanded") !== "true");
    });
    links.addEventListener("click", (event) => {
      if (event.target.closest("a")) setMenu(false);
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") setMenu(false);
    });
    document.addEventListener("click", (event) => {
      if (!links.contains(event.target) && !toggle.contains(event.target)) {
        setMenu(false);
      }
    });
  }

  const legacyCopy = (text) => {
    const area = document.createElement("textarea");
    area.value = text;
    area.setAttribute("readonly", "");
    area.style.position = "fixed";
    area.style.top = "-1000px";
    area.style.opacity = "0";
    document.body.appendChild(area);
    area.select();
    let copied = false;
    try {
      copied = document.execCommand("copy");
    } catch {
      copied = false;
    }
    area.remove();
    return copied;
  };

  document.querySelectorAll("[data-copy]").forEach((button) => {
    button.addEventListener("click", async () => {
      const code = button.closest(".code")?.querySelector("code");
      if (!code) return;
      const text = code.textContent.trimEnd();
      let copied = false;
      try {
        if (navigator.clipboard && window.isSecureContext) {
          await navigator.clipboard.writeText(text);
          copied = true;
        } else {
          copied = legacyCopy(text);
        }
      } catch {
        copied = legacyCopy(text);
      }
      button.textContent = copied ? "已复制" : "复制失败";
      button.classList.toggle("is-done", copied);
      window.clearTimeout(button.copyTimer);
      button.copyTimer = window.setTimeout(() => {
        button.textContent = "复制";
        button.classList.remove("is-done");
      }, 2000);
    });
  });

  const anchorLinks = Array.from(
    document.querySelectorAll('.nav-links a[href^="#"]')
  );
  const sections = anchorLinks
    .map((link) => document.querySelector(link.getAttribute("href")))
    .filter(Boolean);

  let ticking = false;
  const markCurrent = () => {
    ticking = false;
    const line = window.scrollY + 130;
    let current = null;
    for (const section of sections) {
      if (section.offsetTop <= line) current = section;
    }
    for (const link of anchorLinks) {
      if (current && link.getAttribute("href") === `#${current.id}`) {
        link.setAttribute("aria-current", "location");
      } else {
        link.removeAttribute("aria-current");
      }
    }
  };

  if (sections.length) {
    markCurrent();
    window.addEventListener(
      "scroll",
      () => {
        if (!ticking) {
          ticking = true;
          window.requestAnimationFrame(markCurrent);
        }
      },
      { passive: true }
    );
  }

  const revealTargets = document.querySelectorAll(
    ".section-head, .card, .step, .layer, .quick-card, .fit-card, .faq details"
  );

  if (!reduceMotion.matches && "IntersectionObserver" in window) {
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (!entry.isIntersecting) continue;
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      },
      { threshold: 0.12, rootMargin: "0px 0px -6% 0px" }
    );
    const fold = window.innerHeight;
    revealTargets.forEach((target) => {
      if (target.getBoundingClientRect().top > fold + 40) {
        target.classList.add("reveal");
      }
      observer.observe(target);
    });
    window.setTimeout(() => {
      revealTargets.forEach((target) => {
        target.classList.add("is-visible");
        observer.unobserve(target);
      });
    }, 2600);
  }
})();
