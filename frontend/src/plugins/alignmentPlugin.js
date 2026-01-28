
const createAlignMarkdown = (alignType) => (payload, state, dispatch) => {
    const { from, to } = state.selection;
    const text = state.doc.sliceString(from, to);
    const openTag = `<div style="text-align: ${alignType};">`;
    const closeTag = `</div>`;

    // We replace the selection
    const tr = state.tr.replaceWith(from, to, state.schema.text(`${openTag}\n${text}\n${closeTag}`));
    dispatch(tr);
    return true;
};

const createAlignWysiwyg = (alignType) => (payload, state, dispatch) => {
    // In WYSIWYG (ProseMirror), identifying the block and adding a style/node is cleaner,
    // but without schema access to add a custom node type, it's hard.
    // However, we can insert an HTML block if we treat it as raw HTML.

    // Simpler fallback: Just insert the HTML tags around the selection text? 
    // This often converts to text nodes.

    // Let's rely on Toast UI's internal execution if possible, or just skip WYSIWYG specific wrapping
    // and just insert an empty block?

    // Attempt: Insert proper HTML block.
    // NOTE: This might be partial.
    return false;
};

/**
 * Alignment Plugin for Toast UI Editor
 */
export default function alignmentPlugin() {
    return {
        markdownCommands: {
            alignLeft: createAlignMarkdown('left'),
            alignCenter: createAlignMarkdown('center'),
            alignRight: createAlignMarkdown('right'),
        },
        // For WYSIWYG, standard HTML block insertion is tricky without schema extension.
        // We will omit wysiwygCommands -> The toolbar buttons will be disabled in WYSIWYG mode automatically?
        // Or we can try to implement a simple "Insert Block" logic.

        toolbarItems: [
            {
                groupIndex: 3,
                itemIndex: 3,
                item: {
                    name: 'align-left',
                    tooltip: 'Align Left',
                    command: 'alignLeft',
                    className: 'toastui-plugin-align-left',
                    style: { backgroundImage: 'none', width: 'auto', fontSize: '14px', padding: '0 5px' }
                }
            },
            {
                groupIndex: 3,
                itemIndex: 4,
                item: {
                    name: 'align-center',
                    tooltip: 'Align Center',
                    command: 'alignCenter',
                    className: 'toastui-plugin-align-center',
                    style: { backgroundImage: 'none', width: 'auto', fontSize: '14px', padding: '0 5px' }
                }
            },
            {
                groupIndex: 3,
                itemIndex: 5,
                item: {
                    name: 'align-right',
                    tooltip: 'Align Right',
                    command: 'alignRight',
                    className: 'toastui-plugin-align-right',
                    style: { backgroundImage: 'none', width: 'auto', fontSize: '14px', padding: '0 5px' }
                }
            }
        ]
    };
}
