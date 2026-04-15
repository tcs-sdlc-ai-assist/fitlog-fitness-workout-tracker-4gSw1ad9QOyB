# Changelog

All notable changes to the FitLog project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-01-01

### Added

#### Authentication (SCRUM-16665)
- User registration with email and password
- Secure login and logout with JWT-based authentication
- Password hashing with bcrypt for secure credential storage
- Protected routes requiring valid authentication tokens
- Session management and token refresh support

#### Exercise Library (SCRUM-16665)
- Pre-populated exercise database with common exercises
- Exercise categorization by muscle group and equipment type
- Search and filter functionality for finding exercises
- Custom exercise creation for personalized workouts
- Detailed exercise descriptions and instructions

#### Workout Logging (SCRUM-16666)
- Log workouts with date, duration, and notes
- Add multiple exercises per workout session
- Track sets, reps, and weight for each exercise
- Record rest periods between sets
- Support for different exercise types (strength, cardio, flexibility)

#### Workout Templates (SCRUM-16666)
- Create reusable workout templates for recurring routines
- Save any completed workout as a template
- Quick-start workouts from saved templates
- Edit and manage existing templates
- Share templates between workout sessions

#### Body Measurements (SCRUM-16667)
- Track body weight over time
- Record body measurements (chest, waist, hips, arms, legs)
- Log body fat percentage
- Date-stamped measurement entries for historical tracking
- Support for metric and imperial unit systems

#### Progress Tracking (SCRUM-16667)
- Visual charts for weight and measurement trends
- Personal records tracking for each exercise
- Workout volume and frequency analytics
- Progress comparison across custom date ranges
- Strength progression graphs per exercise

#### User Dashboard
- At-a-glance summary of recent activity
- Quick access to start a new workout
- Weekly workout streak and consistency metrics
- Recent personal records display
- Upcoming workout suggestions based on templates

#### Workout History
- Chronological list of all completed workouts
- Detailed view for each past workout session
- Search and filter workout history by date and exercise
- Workout comparison between sessions
- Export workout data for external analysis

#### Admin Dashboard
- User management and account oversight
- System-wide exercise library management
- Usage statistics and platform analytics
- Content moderation tools
- Application health monitoring

#### Mobile-First Navigation
- Responsive bottom navigation bar for mobile devices
- Collapsible sidebar navigation for desktop views
- Touch-friendly interface elements throughout the application
- Swipe gestures for common actions
- Optimized layouts for all screen sizes