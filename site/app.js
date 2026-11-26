(() => {
  const root = document.documentElement;
  root.classList.add("js");

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  if (reduceMotion.matches) {
    root.style.scrollBehavior = "auto";
  }

  const nav = document.querySelector(".nav");
  const toggle = document.querySelector(".nav-toggle");
  const links = document.getElementById("nav-links");

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
    const line = window.scrollY + 140;
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
})();
