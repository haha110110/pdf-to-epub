import React, { forwardRef } from 'react';
import '@toast-ui/editor/dist/toastui-editor.css';
import { Editor } from '@toast-ui/react-editor';

const EditorWrapper = forwardRef(({ initialValue }, ref) => {
    return (
        <div className="h-full w-full">
            <Editor
                ref={ref}
                initialValue={initialValue}
                previewStyle="vertical"
                height="100%"
                initialEditType="wysiwyg"
                useCommandShortcut={true}
                toolbarItems={[
                    ['heading', 'bold', 'italic', 'strike'],
                    ['hr', 'quote'],
                    ['ul', 'ol', 'task', 'indent', 'outdent'],
                    ['table', 'image', 'link'],
                    ['code', 'codeblock']
                ]}
                customHTMLRenderer={{
                    // Custom renderer to enforce Chinese indentation
                    text(node, context) {
                        // Check if text starts with common Chinese punctuation or characters?
                        // Actually easier to just style paragraphs in CSS
                        return { type: 'openTag', tagName: 'span', classNames: ['text-content'] };
                    }
                }}
            />
            {/* Inject Custom Styles for Indentation */}
            <style>{`
        .toastui-editor-contents p {
            text-indent: 2em;
            line-height: 1.8;
            font-size: 16px;
        }
        .toastui-editor-contents img {
            display: block;
            margin: 20px auto;
            max-width: 90%;
            border-radius: 4px;
            box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
        }
        /* Fix full height */
        .toastui-editor-defaultUI {
            height: 100% !important;
        }
      `}</style>
        </div>
    );
});

EditorWrapper.displayName = 'EditorWrapper';
export default EditorWrapper;
