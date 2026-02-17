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

    // Location
    city: "Dallas",
    state: "TX",
    zip: "75019",
    location: "Dallas, TX",
    country: "United States",

    // Education
    school: "The University of Texas at Arlington",
    degree: "Master's",
    major: "Data Science",
    graduationYear: "2023",

    // Demographics
    gender: "Male",
    race: "Asian",
    ethnicity: "Not Hispanic or Latino",
    veteran: "I am not a protected veteran",
    disability: "No, I do not have a disability",

    // Work Authorization
    workAuthorization: "Authorized to work in the US",
    sponsorship: "No",
    securityClearance: "None",

    // Professional
    yearsExperience: "4",
    currentTitle: "Software Engineer",
    startDate: "I am available to start within one week",
    salary: "$100,000"
};

const FieldMappings = {
    // Basic Info
    firstName: ['first_name', 'firstname', 'first name', 'fname', 'given_name'],
    lastName: ['last_name', 'lastname', 'last name', 'lname', 'family_name', 'surname'],
    fullName: ['full_name', 'fullname', 'full name', 'name', 'legal_name'],
    email: ['email', 'e-mail', 'email address', 'email_address', 'e_mail'],
    phone: ['phone', 'mobile', 'cell', 'phone number', 'telephone', 'phone_number'],
    linkedin: ['linkedin', 'linked in', 'linkedin profile', 'linkedin_url'],
    github: ['github', 'git hub', 'github profile', 'github_url'],
    portfolio: ['portfolio', 'website', 'personal site', 'personal_website'],

    // Location
    city: ['city', 'town', 'municipality'],
    state: ['state', 'province', 'region'],
    zip: ['zip', 'zipcode', 'zip_code', 'postal', 'postal_code'],
    location: ['location', 'address', 'city_state', 'current_location'],
    country: ['country', 'nation', 'country_of_residence'],

    // Education
    school: ['school', 'university', 'college', 'institution', 'education'],
    degree: ['degree', 'degree_level', 'education_level'],
    major: ['major', 'field', 'field_of_study', 'concentration'],

    // Demographics
    gender: ['gender', 'sex', 'gender_identity'],
    race: ['race', 'ethnicity', 'racial_background', 'race_ethnicity'],
    ethnicity: ['hispanic', 'latino', 'hispanic_latino', 'hispanic_or_latino'],
    veteran: ['veteran', 'veteran_status', 'military', 'protected_veteran'],
    disability: ['disability', 'disability_status', 'disabled'],

    // Work Authorization
    workAuthorization: ['work_authorization', 'authorized', 'eligible', 'legally_authorized'],
    sponsorship: ['sponsorship', 'require_sponsorship', 'visa_sponsorship', 'sponsor'],
    securityClearance: ['security', 'clearance', 'security_clearance'],

    // Professional
    yearsExperience: ['experience', 'years', 'years_experience', 'years_of_experience'],
    startDate: ['start', 'availability', 'available', 'start_date', 'when_available'],
    salary: ['salary', 'compensation', 'expected_salary', 'desired_salary'],

    // File fields
    resume: ['resume', 'cv', 'curriculum vitae', 'curriculum_vitae'],
    coverLetter: ['cover letter', 'cover_letter', 'cl', 'covering_letter']
};

// Export for usage in other scripts
window.SmartJobApply = {
    Profile: UserProfile,
    Mappings: FieldMappings
};

console.log("⚙️ SmartJobApply Constants Loaded");
