'use client'
import React, { useEffect, useRef } from 'react'

export default function Modal({ children, onClose }: { children: React.ReactNode, onClose: () => void }) {
  const modalRef = useRef<HTMLDivElement>(null);

  // Focus trap and ESC to close
  useEffect(() => {
    const previouslyFocused = document.activeElement as HTMLElement | null;
    const node = modalRef.current;
    if (node) {
      // Focus the modal
      node.focus();
    }
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        onClose();
      }
      // Focus trap
      if (e.key === 'Tab' && node) {
        const focusable = node.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        } else if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        }
      }
    }
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      if (previouslyFocused) previouslyFocused.focus();
    };
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 bg-black bg-opacity-30 flex items-center justify-center"
      role="dialog"
      aria-modal="true"
      aria-label="Modal dialog"
    >
      <div
        ref={modalRef}
        className="bg-white rounded-2xl shadow-2xl p-0 relative w-[96vw] h-[96vh] max-w-none max-h-none overflow-hidden flex flex-col outline-none"
        tabIndex={-1}
      >
        <button
          className="absolute top-3 right-3 text-gray-400 hover:text-gray-800 z-10"
          onClick={onClose}
          aria-label="Close modal"
        >
          &times;
        </button>
        <div className="flex-1 min-h-0 min-w-0 flex flex-col">{children}</div>
      </div>
    </div>
  )
}
