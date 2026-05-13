/** Client-side print / PDF via browser print dialog (Save as PDF). */
export function printDocument(): void {
	if (typeof window !== 'undefined') {
		window.print();
	}
}
