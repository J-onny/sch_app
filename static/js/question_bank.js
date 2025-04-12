// PDF and Image text extraction functions
async function extractTextFromFile() {
    const fileInput = document.getElementById('fileUpload');
    const file = fileInput.files[0];
    if (!file) {
        alert('Please select a file first');
        return;
    }

    // Show loading state
    const button = document.getElementById('extractButton');
    const buttonIcon = button.querySelector('i');
    const buttonText = button.querySelector('span');
    const originalIcon = buttonIcon.className;
    const originalText = buttonText.textContent;

    try {
        // Update button state
        button.disabled = true;
        buttonIcon.className = 'bi bi-hourglass-split';
        buttonText.textContent = 'Extracting...';
        
        let extractedText = '';
        
        if (file.type === 'application/pdf') {
            console.log('Processing PDF file...');
            extractedText = await extractTextFromPDF(file);
        } else if (file.type.startsWith('image/')) {
            console.log('Processing image file...');
            extractedText = await extractTextFromImage(file);
        } else {
            throw new Error('Unsupported file type');
        }

        console.log('Extraction completed');
        
        // Update both plain text and rich editor
        const questionText = document.getElementById('questionText');
        if (questionText) {
            questionText.value = extractedText;
            questionText.dispatchEvent(new Event('input')); // Trigger input event
        }

        if (window.questionEditor) {
            questionEditor.root.innerHTML = extractedText.replace(/\n/g, '<br>');
        }

    } catch (error) {
        console.error('Extraction error:', error);
        alert('Error extracting text from file: ' + error.message);
    } finally {
        // Reset button state
        button.disabled = false;
        buttonIcon.className = originalIcon;
        buttonText.textContent = originalText;
    }
}

async function extractTextFromImage(file) {
    console.log('Starting Tesseract processing...');
    const worker = await Tesseract.createWorker();
    await worker.loadLanguage('eng');
    await worker.initialize('eng');
    
    const { data: { text } } = await worker.recognize(file);
    await worker.terminate();
    
    console.log('Tesseract processing completed');
    return text;
}

async function extractTextFromPDF(file) {
    console.log('Starting PDF processing...');
    const pdfjsLib = window['pdfjs-dist/build/pdf'];
    pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';

    const arrayBuffer = await file.arrayBuffer();
    const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
    let fullText = '';
    
    console.log(`Processing ${pdf.numPages} pages...`);
    
    for (let i = 1; i <= pdf.numPages; i++) {
        console.log(`Processing page ${i}...`);
        const page = await pdf.getPage(i);
        try {
            const textContent = await page.getTextContent();
            const pageText = textContent.items.map(item => item.str).join(' ');
            
            if (pageText.trim()) {
                fullText += pageText + '\n';
            } else {
                console.log(`Page ${i} appears to be image-based, attempting OCR...`);
                const viewport = page.getViewport({ scale: 1.5 });
                const canvas = document.createElement('canvas');
                const context = canvas.getContext('2d');
                canvas.height = viewport.height;
                canvas.width = viewport.width;
                
                await page.render({
                    canvasContext: context,
                    viewport: viewport
                }).promise;
                
                const imageText = await extractTextFromImage(canvas.toDataURL('image/png'));
                fullText += imageText + '\n';
            }
        } catch (error) {
            console.error(`Error processing page ${i}:`, error);
        }
    }
    
    console.log('PDF processing completed');
    return fullText.trim();
}

// Add event listener when the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    const extractButton = document.getElementById('extractButton');
    if (extractButton) {
        extractButton.addEventListener('click', extractTextFromFile);
        console.log('Extract button event listener attached');
    }
}); 