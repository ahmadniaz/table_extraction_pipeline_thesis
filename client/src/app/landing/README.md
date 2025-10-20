# Landing Page & Registration Wizard

This directory contains the landing page and registration wizard implementation for Commission Tracker.

## 🏗️ Structure

```
landing/
├── page.tsx                    # Main landing page
└── README.md                   # This file

register/
├── page.tsx                    # Registration wizard main page
└── components/
    ├── WizardContainer.tsx     # Main wizard container
    ├── StepIndicator.tsx        # Step progress indicator
    ├── PersonalInfoStep.tsx    # Step 1: Personal information
    ├── CompanyInfoStep.tsx     # Step 2: Company information
    ├── EmailVerificationStep.tsx # Step 3: Email verification
    ├── PreferencesStep.tsx     # Step 4: User preferences
    └── WelcomeStep.tsx         # Step 5: Welcome & completion
```

## 🎯 Features

### Landing Page
- **Hero Section**: Compelling headline with CTA buttons
- **Features Section**: Key product features with icons
- **Testimonials**: Customer testimonials and reviews
- **Pricing**: Transparent pricing plans
- **Footer**: Links and company information
- **Responsive Design**: Mobile-first approach
- **Dark Mode**: Full dark/light theme support

### Registration Wizard
- **5-Step Process**: Guided registration experience
- **Step 1**: Personal information (name, email)
- **Step 2**: Company information (name, domain validation)
- **Step 3**: Email verification (OTP integration)
- **Step 4**: User preferences (theme, notifications, timezone)
- **Step 5**: Welcome screen with account summary
- **Progress Indicator**: Visual progress tracking
- **Form Validation**: Real-time validation with error messages
- **Responsive Design**: Works on all device sizes

## 🔧 Technical Implementation

### Components
- **WizardContainer**: Main container with animations
- **StepIndicator**: Progress bar with step navigation
- **Form Steps**: Individual step components with validation
- **Navigation**: Previous/Next buttons with state management

### State Management
- **WizardData Interface**: TypeScript interface for form data
- **useState**: Local state management for form data
- **Context Integration**: Uses existing AuthContext and ThemeContext

### Styling
- **Tailwind CSS**: Utility-first CSS framework
- **Framer Motion**: Smooth animations and transitions
- **Responsive Design**: Mobile-first approach
- **Dark Mode**: Full theme support

## 🚀 Usage

### Landing Page
```tsx
// Navigate to landing page
router.push('/landing');
```

### Registration Wizard
```tsx
// Navigate to registration wizard
router.push('/register');
```

### Integration with Existing Auth
The wizard integrates with the existing authentication system:
- Uses `AuthContext` for OTP functionality
- Reuses existing OTP verification logic
- Maintains compatibility with current auth flow

## 📱 Responsive Design

- **Mobile**: Optimized for mobile devices
- **Tablet**: Responsive grid layouts
- **Desktop**: Full-featured experience
- **Touch**: Touch-friendly interactions

## 🎨 Theming

- **Light Mode**: Clean, professional appearance
- **Dark Mode**: Easy on the eyes
- **System Mode**: Follows system preference
- **Smooth Transitions**: Animated theme switching

## 🔒 Security

- **OTP Verification**: Secure email verification
- **Domain Validation**: Company domain verification
- **Form Validation**: Client-side and server-side validation
- **Secure Cookies**: HTTP-only cookies for authentication

## 🧪 Testing

- **Form Validation**: Test all form fields
- **Navigation**: Test step navigation
- **Responsive**: Test on different screen sizes
- **Themes**: Test light/dark mode switching
- **Integration**: Test with existing auth system

## 🚀 Deployment

The landing page and registration wizard are ready for deployment:
- No additional dependencies required
- Uses existing project structure
- Compatible with current build process
- SEO-friendly implementation

## 📈 Analytics

Consider adding analytics tracking for:
- Landing page conversions
- Wizard completion rates
- Step abandonment points
- User preferences
- Form validation errors

## 🔄 Future Enhancements

- **A/B Testing**: Test different landing page versions
- **Multi-language**: Internationalization support
- **Advanced Validation**: Server-side validation
- **Email Templates**: Customized email templates
- **Onboarding**: Post-registration onboarding flow
