async function loadSubjects() {
    try {
        // Get subjects from the syllabi directory structure
        const subjectSelect = document.getElementById('subjectSelect');
        subjectSelect.innerHTML = '<option value="">Select Subject</option>';
        
        // These are the actual subject folders from your syllabi directory
        const subjects = [
            'Agriculture',
            'Art & Design',
            'Biology',
            'Chemistry',
            'English',
            'Entrepreneurship',
            'Geography',
            'History',
            'Kiswahili',
            'Literature',
            'Mathematics',
            'Physics',
            'Technical Drawing'
        ];
        
        subjects.forEach(subject => {
            const option = document.createElement('option');
            option.value = subject.toLowerCase().replace(' & ', '_and_');
            option.textContent = subject;
            subjectSelect.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading subjects:', error);
    }
}

async function loadGrades(subject) {
    try {
        const gradeSelect = document.getElementById('gradeSelect');
        gradeSelect.innerHTML = '<option value="">Select Grade</option>';
        
        // Standard grades for all subjects
        const grades = [
            'Senior 1',
            'Senior 2',
            'Senior 3',
            'Senior 4'
        ];
        
        grades.forEach(grade => {
            const option = document.createElement('option');
            option.value = grade.toLowerCase().replace(' ', '');
            option.textContent = grade;
            gradeSelect.appendChild(option);
        });
        
        gradeSelect.disabled = false;
    } catch (error) {
        console.error('Error loading grades:', error);
    }
}

async function loadTopics(subject, grade) {
    try {
        // Convert subject and grade to match file structure
        const formattedSubject = subject.charAt(0).toUpperCase() + subject.slice(1)
            .replace('_and_', ' & ');
        const formattedGrade = grade.replace('senior', 'senior_') + '.json';
        
        // Fetch the syllabus JSON file
        const response = await fetch(`/static/syllabi/${formattedSubject}/${formattedGrade}`);
        const syllabus = await response.json();
        
        const topicSelect = document.getElementById('topicSelect');
        topicSelect.innerHTML = '<option value="">Select Topic</option>';
        
        // Extract unique topics from the syllabus
        const topics = new Set();
        syllabus.forEach(item => {
            if (item.topic) {
                topics.add(item.topic);
            }
        });
        
        // Add topics to select
        Array.from(topics).sort().forEach(topic => {
            const option = document.createElement('option');
            option.value = topic.toLowerCase().replace(/\s+/g, '_');
            option.textContent = topic;
            topicSelect.appendChild(option);
        });
        
        topicSelect.disabled = false;
    } catch (error) {
        console.error('Error loading topics:', error);
        // If there's an error loading topics, show an alert
        alert('Error loading topics for the selected subject and grade. Please try again.');
    }
}

// Initialize event listeners
document.addEventListener('DOMContentLoaded', function() {
    const subjectSelect = document.getElementById('subjectSelect');
    const gradeSelect = document.getElementById('gradeSelect');
    const topicSelect = document.getElementById('topicSelect');
    
    // Load subjects when the page loads
    loadSubjects();
    
    // Handle subject selection
    subjectSelect.addEventListener('change', function() {
        const subject = this.value;
        gradeSelect.value = '';
        topicSelect.value = '';
        
        if (subject) {
            loadGrades(subject);
            topicSelect.disabled = true;
        } else {
            gradeSelect.disabled = true;
            topicSelect.disabled = true;
        }
    });
    
    // Handle grade selection
    gradeSelect.addEventListener('change', function() {
        const subject = subjectSelect.value;
        const grade = this.value;
        topicSelect.value = '';
        
        if (grade && subject) {
            loadTopics(subject, grade);
        } else {
            topicSelect.disabled = true;
        }
    });
}); 