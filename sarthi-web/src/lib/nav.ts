export type NavItem = { href: "/chat" | "/sop"; label: string; icon: "chat" | "doc" };

export const APP_NAV: NavItem[] = [
  { href: "/chat", label: "Chat", icon: "chat" },
  { href: "/sop", label: "SOP", icon: "doc" },
];
