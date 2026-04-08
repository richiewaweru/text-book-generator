import type { Snippet } from 'svelte';
interface Props {
    value: string;
    children?: Snippet;
    class?: string;
}
declare const AccordionItem: import("svelte").Component<Props, {}, "">;
type AccordionItem = ReturnType<typeof AccordionItem>;
export default AccordionItem;
