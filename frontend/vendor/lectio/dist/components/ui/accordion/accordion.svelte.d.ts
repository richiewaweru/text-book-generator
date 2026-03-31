import { type AccordionRootProps } from 'bits-ui';
import type { Snippet } from 'svelte';
type $$ComponentProps = AccordionRootProps & {
    children?: Snippet;
    class?: string;
};
declare const Accordion: import("svelte").Component<$$ComponentProps, {}, "">;
type Accordion = ReturnType<typeof Accordion>;
export default Accordion;
