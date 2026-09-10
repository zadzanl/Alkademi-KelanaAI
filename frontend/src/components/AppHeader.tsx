"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { logoutFormAction } from "../app/actions";

type AppHeaderProps = { username?: string | null };
const links = [
  { href: "/", label: "Planner" },
  { href: "/trips", label: "My Trips" },
  { href: "/chat", label: "Assistant" },
];

export function AppHeader({ username }: AppHeaderProps) {
  const pathname = usePathname();
  const [navOpen, setNavOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [theme, setTheme] = useState<"light" | "dark">("light");
  const headerRef = useRef<HTMLElement>(null);
  const menuButtonRef = useRef<HTMLButtonElement>(null);
  const profileTriggerRef = useRef<HTMLButtonElement>(null);
  const profileMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setTheme(
      (document.documentElement.getAttribute("data-theme") as "light" | "dark") || "light"
    );
  }, []);

  const toggleTheme = () => {
    const next = theme === "light" ? "dark" : "light";
    setTheme(next);
    document.documentElement.setAttribute("data-theme", next);
    try {
      localStorage.setItem("kelana_theme", next);
    } catch {}
  };

  useEffect(() => {
    if (!navOpen && !profileOpen) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        if (profileOpen) {
          setProfileOpen(false);
          profileTriggerRef.current?.focus();
        }
        if (navOpen) {
          setNavOpen(false);
          menuButtonRef.current?.focus();
        }
      }
    };
    const handleClickOutside = (event: MouseEvent | TouchEvent) => {
      const target = event.target as Node;
      if (headerRef.current && !headerRef.current.contains(target)) {
        setNavOpen(false);
        setProfileOpen(false);
      } else if (profileOpen && profileMenuRef.current && !profileMenuRef.current.contains(target)) {
        setProfileOpen(false);
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("touchstart", handleClickOutside);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("touchstart", handleClickOutside);
    };
  }, [navOpen, profileOpen]);

  const profileInitial = username?.trim().charAt(0).toUpperCase() || "G";

  return (
    <header className="app-header" ref={headerRef}>
      <a href="#main-content" className="skip-link">
        Skip to content
      </a>
      <nav className="app-header__inner" aria-label="Primary">
        <Link
          href="/"
          className="font-display text-2xl text-ink hover:text-terracotta-dark"
          onClick={() => {
            setNavOpen(false);
            setProfileOpen(false);
          }}
        >
          Kelana<span className="text-terracotta-dark">AI</span>
        </Link>
        <div className="flex items-center gap-3">
          <button
            ref={menuButtonRef}
            type="button"
            className="app-header__menu"
            aria-expanded={navOpen}
            aria-controls="primary-navigation"
            onClick={() => setNavOpen((value) => !value)}
          >
            <span className="sr-only">Toggle navigation</span>
            {navOpen ? "Close" : "Menu"}
          </button>
        </div>
        <div
          id="primary-navigation"
          className={`app-header__nav ${navOpen ? "app-header__nav--open" : ""}`}
        >
          {links.map((link) => {
            const active =
              link.href === "/"
                ? pathname === "/"
                : pathname.startsWith(link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                aria-current={active ? "page" : undefined}
                className={`app-header__link ${
                  active ? "app-header__link--active" : ""
                }`}
                onClick={() => {
                  setNavOpen(false);
                  setProfileOpen(false);
                }}
              >
                {link.label}
              </Link>
            );
          })}
          {username ? (
            <div
              ref={profileMenuRef}
              className="profile-menu"
            >
              <button
                ref={profileTriggerRef}
                type="button"
                className="profile-menu__trigger"
                aria-expanded={profileOpen}
                aria-haspopup="menu"
                onClick={() => setProfileOpen((value) => !value)}
              >
                <span className="profile-menu__avatar" aria-hidden="true">
                  {profileInitial}
                </span>
                <span className="profile-menu__name">{username}</span>
                <svg
                  className="profile-menu__chevron"
                  viewBox="0 0 12 8"
                  aria-hidden="true"
                  focusable="false"
                >
                  <path d="m1 1 5 5 5-5" />
                </svg>
              </button>
              <div
                className={`profile-menu__popover ${
                  profileOpen ? "profile-menu__popover--open" : ""
                }`}
                role="menu"
              >
                <Link
                  href="/trips"
                  role="menuitem"
                  className="profile-menu__item"
                  onClick={() => {
                    setNavOpen(false);
                    setProfileOpen(false);
                  }}
                >
                  Manage profile
                </Link>
                <form action={logoutFormAction}>
                  <button
                    className="profile-menu__item"
                    type="submit"
                    role="menuitem"
                  >
                    Sign out
                  </button>
                </form>
                <button
                  type="button"
                  role="menuitem"
                  className="profile-menu__item"
                  onClick={() => {
                    toggleTheme();
                    setProfileOpen(false);
                  }}
                >
                  {theme === "light" ? "Dark mode" : "Light mode"}
                </button>
              </div>
            </div>
          ) : (
            <Link
              href="/auth"
              className={`app-header__link ${
                pathname.startsWith("/auth") ? "app-header__link--active" : ""
              }`}
              aria-current={pathname.startsWith("/auth") ? "page" : undefined}
              onClick={() => {
                setNavOpen(false);
                setProfileOpen(false);
              }}
            >
              Sign in
            </Link>
          )}
          <button
            type="button"
            className="app-header__theme-btn"
            onClick={toggleTheme}
            aria-label={theme === "light" ? "Switch to dark mode" : "Switch to light mode"}
            title={theme === "light" ? "Switch to dark mode" : "Switch to light mode"}
          >
            {theme === "light" ? (
              <>
                <svg
                  className="h-3.5 w-3.5 text-terracotta"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth="2"
                  aria-hidden="true"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"
                  />
                </svg>
                <span className="hidden sm:inline">Dark</span>
              </>
            ) : (
              <>
                <svg
                  className="h-3.5 w-3.5 text-terracotta-dark"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth="2"
                  aria-hidden="true"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"
                  />
                </svg>
                <span className="hidden sm:inline">Light</span>
              </>
            )}
          </button>
        </div>
      </nav>
    </header>
  );
}