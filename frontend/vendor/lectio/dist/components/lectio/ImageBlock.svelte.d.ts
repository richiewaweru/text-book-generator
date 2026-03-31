import type { MediaReference } from '../../document';
import type { ImageBlockContent } from '../../types';
type $$ComponentProps = {
    content: ImageBlockContent;
    media?: Record<string, MediaReference>;
};
declare const ImageBlock: import("svelte").Component<$$ComponentProps, {}, "">;
type ImageBlock = ReturnType<typeof ImageBlock>;
export default ImageBlock;
