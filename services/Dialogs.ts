/**
 * Promise-based in-app prompt.
 *
 * Native window.prompt() is unavailable in iOS standalone PWAs and in several
 * embedded webviews, where it silently returns null and breaks the flow.
 * This helper renders a small accessible dialog instead, so field staff can
 * always complete the action.
 */
export interface PromptOptions {
  title?: string;
  placeholder?: string;
  defaultValue?: string;
  confirmLabel?: string;
  cancelLabel?: string;
}

export function promptDialog(message: string, options: PromptOptions = {}): Promise<string | null> {
  const {
    title = 'Input required',
    placeholder = '',
    defaultValue = '',
    confirmLabel = 'Confirm',
    cancelLabel = 'Cancel',
  } = options;

  return new Promise((resolve) => {
    const overlay = document.createElement('div');
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.className = 'fixed inset-0 z-[999] flex items-center justify-center bg-black/50 p-4';

    overlay.innerHTML = `
      <form class="bg-white w-full max-w-md rounded-2xl shadow-xl overflow-hidden">
        <div class="p-5 border-b border-gray-100">
          <h3 class="text-base font-bold text-gray-900"></h3>
          <p class="text-sm text-gray-500 mt-1"></p>
        </div>
        <div class="p-5">
          <input type="text" class="w-full rounded-lg border border-gray-300 p-2 text-sm focus:border-brandBlue focus:ring-brandBlue" />
        </div>
        <div class="p-4 bg-gray-50 flex justify-end gap-2">
          <button type="button" data-action="cancel" class="px-4 py-2 text-sm font-medium border border-gray-300 rounded-lg text-gray-700 hover:bg-white"></button>
          <button type="submit" data-action="confirm" class="px-4 py-2 text-sm font-medium bg-brandBlue text-white rounded-lg hover:bg-blue-600"></button>
        </div>
      </form>
    `;

    const titleEl = overlay.querySelector('h3') as HTMLElement;
    const messageEl = overlay.querySelector('p') as HTMLElement;
    const input = overlay.querySelector('input') as HTMLInputElement;
    const cancelButton = overlay.querySelector('[data-action="cancel"]') as HTMLButtonElement;
    const confirmButton = overlay.querySelector('[data-action="confirm"]') as HTMLButtonElement;

    titleEl.textContent = title;
    messageEl.textContent = message;
    input.placeholder = placeholder;
    input.value = defaultValue;
    cancelButton.textContent = cancelLabel;
    confirmButton.textContent = confirmLabel;

    const cleanup = (value: string | null) => {
      document.removeEventListener('keydown', onKeyDown, true);
      overlay.remove();
      resolve(value);
    };

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        cleanup(null);
      }
    };

    overlay.querySelector('form')!.addEventListener('submit', (event) => {
      event.preventDefault();
      const value = input.value.trim();
      cleanup(value === '' ? null : value);
    });
    cancelButton.addEventListener('click', () => cleanup(null));
    overlay.addEventListener('mousedown', (event) => {
      if (event.target === overlay) cleanup(null);
    });
    document.addEventListener('keydown', onKeyDown, true);

    document.body.appendChild(overlay);
    input.focus();
    input.select();
  });
}
