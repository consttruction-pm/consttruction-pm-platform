# ConstructionPM Desktop Application

This directory is reserved for the Desktop Application client.

## Contract
- Uses the same shared API/Application contracts as the Web Application.
- No direct database access for business operations.
- No independent scheduling/progress/EVM/resource/cost calculations.
- Must support Persian/English and Jalali/Gregorian presentation.
- Must respect permissions and ProjectContext.
- Must preserve typed values and offline capabilities that are explicitly approved by product architecture.

## Feature parity
Business capabilities must match the Web Application. Platform-specific UI/interaction differences are allowed; business semantics are not.

## Ownership
Primary client implementation: User/Product Client Track.
Backend/API contracts: Hasan.
