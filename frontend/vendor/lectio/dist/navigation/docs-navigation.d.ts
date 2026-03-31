export interface DocsNavItem {
    href: string;
    label: string;
    meta: string;
}
export interface DocsNavGroup {
    eyebrow: string;
    items: DocsNavItem[];
}
/** Primary documentation IA — used by sidebar and mobile doc nav. */
export declare function getDocsNavigation(): DocsNavGroup[];
export declare function flattenDocsNavItems(): DocsNavItem[];
