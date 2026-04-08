import type { Snippet } from 'svelte';
import type { SectionContent } from '../types';
type $$ComponentProps = {
    section: SectionContent;
    children: Snippet;
    sidebar?: Snippet;
    singleColumn?: boolean;
    contentClassName?: string;
};
declare const TemplateShell: import("svelte").Component<$$ComponentProps, {}, "">;
type TemplateShell = ReturnType<typeof TemplateShell>;
export default TemplateShell;
