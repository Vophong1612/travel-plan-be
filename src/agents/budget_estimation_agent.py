import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.agents.base_agent import BaseAgent, AgentMessage, AgentResponse
from src.agents.user_intent_agent import TravelContext


class BudgetEstimationAgent(BaseAgent):
    """Agent responsible for calculating estimated budgets for travel itineraries."""
    
    def __init__(self):
        super().__init__(
            agent_id="budget_estimation",
            name="Budget Calculator",
            description="Calculates daily and total costs using price ranges and traveler count",
            tools=[]  # This agent uses calculation logic, no external tools needed
        )
        
        # Cost multipliers by location (rough cost of living adjustments)
        self.location_cost_multipliers = {
            # High cost cities
            "new york": 1.3,
            "san francisco": 1.4,
            "london": 1.2,
            "paris": 1.2,
            "tokyo": 1.3,
            "zurich": 1.5,
            "singapore": 1.2,
            
            # Medium cost cities
            "chicago": 1.1,
            "seattle": 1.1,
            "berlin": 1.0,
            "amsterdam": 1.1,
            "sydney": 1.2,
            
            # Lower cost cities
            "bangkok": 0.6,
            "budapest": 0.7,
            "prague": 0.8,
            "mexico city": 0.7,
            "mumbai": 0.5,
        }
        
        # Default cost estimates by activity type (in USD per person)
        self.default_activity_costs = {
            "cultural": 15,     # Museums, galleries
            "sightseeing": 10,  # Tourist attractions
            "outdoor": 5,       # Parks, hiking (often free)
            "entertainment": 25, # Shows, activities
            "shopping": 0,      # Variable, usually no entry cost
            "dining": 25,       # Average meal cost
            "accommodation": 80, # Per night (not used in current scope)
            "transport": 15     # Local transport per day
        }
        
        # Budget level multipliers
        self.budget_multipliers = {
            "budget": 0.7,      # 30% less than default
            "mid-range": 1.0,   # Default costs
            "luxury": 1.8       # 80% more than default
        }
    
    def get_prompt_template(self) -> str:
        """Get the agent's prompt template."""
        return """
        You are an AI assistant specializing in travel budget estimation.
        
        Your tasks:
        1. Calculate estimated costs for each activity in the proposed itinerary
        2. Apply location-based cost adjustments
        3. Multiply costs by the number of travelers
        4. Generate daily and total budget breakdowns
        5. Provide budget insights and recommendations
        
        Consider user's budget level, destination cost of living, and group size.
        Provide transparent cost breakdowns and helpful budget guidance.
        """
    
    async def execute(self, message: AgentMessage) -> AgentResponse:
        """Execute the budget estimation agent's functionality."""
        message_type = message.message_type
        content = message.content
        
        if message_type == "calculate_budget":
            return await self._calculate_budget(content)
        else:
            return self._create_error_response(f"Unknown message type: {message_type}")
    
    async def _calculate_budget(self, content: Dict[str, Any]) -> AgentResponse:
        """Calculate estimated budget for the proposed itinerary."""
        try:
            # Get travel context
            travel_context_data = content.get("travel_context")
            if not travel_context_data:
                return self._create_error_response("travel_context is required")
            
            # Recreate TravelContext object
            travel_context = TravelContext(**travel_context_data)
            
            if not travel_context.proposed_itinerary:
                return self._create_error_response("proposed_itinerary is required in travel_context")
            
            # Calculate budget breakdown
            budget_breakdown = await self._calculate_detailed_budget(travel_context)
            
            # Calculate totals
            total_estimated_budget = budget_breakdown.get("total_cost", 0)
            daily_average_budget = total_estimated_budget / max(travel_context.duration, 1)
            
            # Update travel context
            travel_context.estimated_budget_breakdown = budget_breakdown
            travel_context.total_estimated_budget = total_estimated_budget
            travel_context.daily_average_budget = daily_average_budget
            
            return self._create_success_response({
                "travel_context": travel_context.__dict__,
                "budget_summary": {
                    "total_estimated_budget": total_estimated_budget,
                    "daily_average_budget": daily_average_budget,
                    "budget_level": travel_context.budget_level,
                    "travelers": travel_context.travelers,
                    "currency": "USD"
                },
                "budget_insights": self._generate_budget_insights(travel_context, budget_breakdown)
            })
            
        except Exception as e:
            self.logger.error(f"Error calculating budget: {str(e)}")
            return self._create_error_response(f"Failed to calculate budget: {str(e)}")
    
    async def _calculate_detailed_budget(self, travel_context: TravelContext) -> Dict[str, Any]:
        """Calculate detailed budget breakdown."""
        try:
            # Get cost multiplier for location
            location_multiplier = self._get_location_cost_multiplier(travel_context.destination)
            
            # Get budget level multiplier
            budget_multiplier = self.budget_multipliers.get(travel_context.budget_level, 1.0)
            
            # Calculate costs by category
            daily_breakdowns = []
            category_totals = {
                "dining": 0,
                "attractions": 0,
                "activities": 0,
                "entertainment": 0,
                "shopping": 0,
                "transport": 0
            }
            
            # Process each day
            for day in travel_context.proposed_itinerary:
                daily_breakdown = await self._calculate_daily_budget(
                    day, 
                    travel_context.travelers,
                    location_multiplier,
                    budget_multiplier
                )
                daily_breakdowns.append(daily_breakdown)
                
                # Add to category totals
                for category, amount in daily_breakdown.get("categories", {}).items():
                    if category in category_totals:
                        category_totals[category] += amount
            
            # Calculate total cost
            total_cost = sum(day.get("total_cost", 0) for day in daily_breakdowns)
            
            return {
                "daily_breakdowns": daily_breakdowns,
                "category_totals": category_totals,
                "total_cost": total_cost,
                "travelers": travel_context.travelers,
                "budget_level": travel_context.budget_level,
                "location_multiplier": location_multiplier,
                "budget_multiplier": budget_multiplier,
                "currency": "USD",
                "calculated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating detailed budget: {str(e)}")
            return {
                "error": str(e),
                "total_cost": 0,
                "daily_breakdowns": [],
                "category_totals": {}
            }
    
    async def _calculate_daily_budget(self, day: Dict[str, Any], travelers: int, 
                                    location_multiplier: float, budget_multiplier: float) -> Dict[str, Any]:
        """Calculate budget for a single day."""
        try:
            activities = day.get("activities", [])
            
            categories = {
                "dining": 0,
                "attractions": 0,
                "activities": 0,
                "entertainment": 0,
                "shopping": 0,
                "transport": 0
            }
            
            activity_costs = []
            
            for activity in activities:
                # Get activity cost
                cost_per_person = self._get_activity_cost(activity, location_multiplier, budget_multiplier)
                total_cost = cost_per_person * travelers
                
                # Categorize cost
                category = self._categorize_activity_cost(activity)
                categories[category] += total_cost
                
                activity_costs.append({
                    "name": activity.get("name", "Unknown"),
                    "type": activity.get("type", "unknown"),
                    "cost_per_person": cost_per_person,
                    "total_cost": total_cost,
                    "category": category
                })
            
            # Add daily transport allowance if no transport activities
            if categories["transport"] == 0:
                transport_cost = self.default_activity_costs["transport"] * location_multiplier * budget_multiplier * travelers
                categories["transport"] += transport_cost
                activity_costs.append({
                    "name": "Local Transportation",
                    "type": "transport",
                    "cost_per_person": transport_cost / travelers,
                    "total_cost": transport_cost,
                    "category": "transport"
                })
            
            total_cost = sum(categories.values())
            
            return {
                "day_index": day.get("day_index", 1),
                "date": day.get("date"),
                "theme": day.get("theme", ""),
                "categories": categories,
                "activity_costs": activity_costs,
                "total_cost": total_cost,
                "cost_per_person": total_cost / travelers if travelers > 0 else total_cost
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating daily budget: {str(e)}")
            return {
                "day_index": day.get("day_index", 1),
                "date": day.get("date"),
                "categories": {},
                "activity_costs": [],
                "total_cost": 0,
                "cost_per_person": 0
            }
    
    def _get_activity_cost(self, activity: Dict[str, Any], location_multiplier: float, budget_multiplier: float) -> float:
        """Get estimated cost for an activity per person."""
        # First, check if activity has explicit cost
        explicit_cost = activity.get("cost")
        if explicit_cost and explicit_cost > 0:
            return explicit_cost * location_multiplier * budget_multiplier
        
        # Otherwise, use default cost for activity type
        activity_type = activity.get("type", "sightseeing")
        default_cost = self.default_activity_costs.get(activity_type, 15)
        
        # Apply multipliers
        estimated_cost = default_cost * location_multiplier * budget_multiplier
        
        return round(estimated_cost, 2)
    
    def _categorize_activity_cost(self, activity: Dict[str, Any]) -> str:
        """Categorize activity cost for budget breakdown."""
        activity_type = activity.get("type", "").lower()
        
        if activity_type == "dining":
            return "dining"
        elif activity_type in ["cultural", "sightseeing"]:
            return "attractions"
        elif activity_type == "entertainment":
            return "entertainment"
        elif activity_type == "shopping":
            return "shopping"
        elif activity_type == "outdoor":
            return "activities"
        elif activity_type == "transport":
            return "transport"
        else:
            return "activities"  # Default category
    
    def _get_location_cost_multiplier(self, destination: str) -> float:
        """Get cost multiplier based on destination."""
        if not destination:
            return 1.0
        
        destination_lower = destination.lower()
        
        # Check for exact matches or partial matches
        for location, multiplier in self.location_cost_multipliers.items():
            if location in destination_lower:
                return multiplier
        
        # Default multiplier for unknown locations
        return 1.0
    
    def _generate_budget_insights(self, travel_context: TravelContext, budget_breakdown: Dict[str, Any]) -> Dict[str, Any]:
        """Generate budget insights and recommendations."""
        insights = {
            "recommendations": [],
            "warnings": [],
            "tips": [],
            "comparison": {}
        }
        
        try:
            total_cost = budget_breakdown.get("total_cost", 0)
            daily_average = total_cost / max(travel_context.duration, 1)
            travelers = travel_context.travelers
            budget_level = travel_context.budget_level
            
            # Per person daily cost
            daily_per_person = daily_average / travelers if travelers > 0 else daily_average
            
            # Budget level analysis
            if budget_level == "budget" and daily_per_person > 80:
                insights["warnings"].append("Daily costs may exceed budget expectations - consider more economical options")
            elif budget_level == "luxury" and daily_per_person < 150:
                insights["recommendations"].append("Room for premium experiences within luxury budget")
            
            # Category analysis
            category_totals = budget_breakdown.get("category_totals", {})
            
            # Dining analysis
            dining_cost = category_totals.get("dining", 0)
            dining_percentage = (dining_cost / total_cost * 100) if total_cost > 0 else 0
            
            if dining_percentage > 50:
                insights["warnings"].append("High proportion of budget on dining - consider mixing restaurant types")
            elif dining_percentage < 25:
                insights["recommendations"].append("Budget allows for more diverse dining experiences")
            
            # Activities analysis
            activities_cost = category_totals.get("attractions", 0) + category_totals.get("activities", 0)
            activities_percentage = (activities_cost / total_cost * 100) if total_cost > 0 else 0
            
            if activities_percentage < 30:
                insights["recommendations"].append("Consider adding more paid activities or attractions")
            
            # Group size considerations
            if travelers > 4:
                insights["tips"].append("Look for group discounts at attractions and restaurants")
                insights["tips"].append("Consider family-style dining to reduce costs")
            
            # Destination-specific tips
            destination_lower = travel_context.destination.lower() if travel_context.destination else ""
            
            if any(city in destination_lower for city in ["new york", "london", "paris", "tokyo"]):
                insights["tips"].append("High-cost city: Consider lunch specials and happy hour deals")
                insights["tips"].append("Many world-class museums offer free or discounted hours")
            
            # Budget comparison
            budget_ranges = {
                "budget": (40, 80),      # Per person per day
                "mid-range": (80, 150),
                "luxury": (150, 300)
            }
            
            expected_range = budget_ranges.get(budget_level, (80, 150))
            insights["comparison"] = {
                "expected_daily_range": expected_range,
                "actual_daily_per_person": round(daily_per_person, 2),
                "within_range": expected_range[0] <= daily_per_person <= expected_range[1],
                "variance_percentage": round(((daily_per_person - expected_range[1]) / expected_range[1] * 100), 1) if daily_per_person > expected_range[1] else 0
            }
            
            # Money-saving tips
            insights["tips"].extend([
                "Book attraction tickets online for potential discounts",
                "Use public transportation for cost-effective city travel",
                "Consider picnic lunches in parks to save on meal costs"
            ])
            
        except Exception as e:
            self.logger.error(f"Error generating budget insights: {str(e)}")
            insights["error"] = str(e)
        
        return insights
    
    def _format_cost(self, amount: float) -> str:
        """Format cost as USD string."""
        return f"${amount:.2f}"
    
    def _calculate_cost_per_traveler(self, total_cost: float, travelers: int) -> float:
        """Calculate cost per traveler."""
        return total_cost / travelers if travelers > 0 else total_cost 