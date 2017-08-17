Feature: Admin Authentication

	Scenario: Logging in to the Admin as an admin
		Given a staff user
		When I log in
		Then I should see "Dashboard"
	
	Scenario: Logging in to the Admin as a regular user
		Given a regular user
		When I log in
		Then I see an error message

	Scenario: Logging in to the Admin without an account
		Given a fake user
		When I log in
		Then I see an error message

	Scenario: Logging out of the Admin
		Given a staff user
		When I log in
		Then I should see "Dashboard"
		When I log out
		Then I see the home page