export type NavItem = {
  href: "/chat" | "/sop" | "/loan" | "/apply";
  label: string;
  icon: "chat" | "doc" | "wallet" | "file";
};

export const APP_NAV: NavItem[] = [
  { href: "/chat", label: "Chat", icon: "chat" },
  { href: "/sop", label: "SOP", icon: "doc" },
  { href: "/loan", label: "Loan", icon: "wallet" },
  { href: "/apply", label: "Apply", icon: "file" },
];
