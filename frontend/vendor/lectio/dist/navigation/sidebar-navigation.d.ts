export interface SidebarNavigationItem {
    href: string;
    label: string;
    meta: string;
}
export interface SidebarNavigationData {
    components: SidebarNavigationItem[];
    templates: SidebarNavigationItem[];
}
export declare function getSidebarNavigation(): SidebarNavigationData;
