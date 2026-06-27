export type NavItem = {
  href: "/chat" | "/sop" | "/loan";
  label: string;
  icon: "chat" | "doc" | "wallet";
};

export const APP_NAV: NavItem[] = [
  { href: "/chat", label: "Chat", icon: "chat" },
  { href: "/sop", label: "SOP", icon: "doc" },
  { href: "/loan", label: "Loan", icon: "wallet" },
];
