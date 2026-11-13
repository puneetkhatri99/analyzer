import { useEffect } from "react";

// Section entrances: the parts of each [data-reveal] block rise in, in reading order, once, as it scrolls into view.
// Off when the visitor asks for reduced motion; the content is then simply there.
export const MOTION = typeof window !== "undefined" && !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
if (MOTION) document.documentElement.classList.add("mh-motion");

// Call with whatever makes new blocks appear (the loaded report), so they are watched too.
export function useReveal(dep) {
  useEffect(() => {
    if (!MOTION) return undefined;
    const io = new IntersectionObserver((entries) => entries.forEach((e) => {
      if (e.isIntersecting) { e.target.classList.add("is-in"); io.unobserve(e.target); }
    }), { rootMargin: "0px 0px -8% 0px" });
    document.querySelectorAll("[data-reveal]:not(.is-in)").forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, [dep]);
}
