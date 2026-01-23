/**
 * constants.js
 * Centralized configuration for SmartJobApply Extension.
 * Contains user profile and field mapping keywords.
 */

const HOST_NAME = 'com.smartjobapply.folder_reader';

const UserProfile = {
    // Basic Info
    firstName: "Nuthan Reddy",
    lastName: "Vaddi Reddy",
    fullName: "Nuthan Reddy Vaddi Reddy",
    email: "nuthanreddy001@gmail.com",
    phone: "+1 682-406-5646",
    linkedin: "https://www.linkedin.com/in/nuthan-reddy-vaddi-reddy/",
    github: "http://github.com/Nuthanreddy05",
    city: "Dallas",
    state: "TX",
    zip: "75019", // Added per user request

    // Education
    school: "The University of Texas at Arlington",
    degree: "Master's",
    major: "Data Science"
};

const FieldMappings = {
    firstName: ['first_name', 'firstname', 'first name', 'fname'],
    lastName: ['last_name', 'lastname', 'last name', 'lname'],
    fullName: ['full_name', 'fullname', 'full name', 'name'],
    email: ['email', 'e-mail', 'email address'],
    phone: ['phone', 'mobile', 'cell', 'phone number'],
    linkedin: ['linkedin', 'linked in', 'linkedin profile'],
    github: ['github', 'git hub', 'github profile'],
    portfolio: ['portfolio', 'website', 'personal site'],
    resume: ['resume', 'cv', 'curriculum vitae'],
    coverLetter: ['cover letter', 'cover_letter', 'cl']
};

// Export for usage in other scripts
window.SmartJobApply = {
    Profile: UserProfile,
    Mappings: FieldMappings
};

console.log("⚙️ SmartJobApply Constants Loaded");
