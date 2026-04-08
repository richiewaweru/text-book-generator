import type { Snippet } from 'svelte';
import type { HTMLAttributes } from 'svelte/elements';
interface Props extends HTMLAttributes<HTMLParagraphElement> {
    children?: Snippet;
    class?: string;
}
declare const AlertDescription: import("svelte").Component<Props, {}, "">;
type AlertDescription = ReturnType<typeof AlertDescription>;
export default AlertDescription;
