
import os, random
from flask import Flask,jsonify,Response,request
from flask_restx import Api,Resource

from pandas import read_feather
from pandas.core.frame import DataFrame
from rapidfuzz import fuzz
from rapidfuzz import process

# Internal imports
from db.user import User
from api.load_data import get_recipe_lookup

# configuration
DEBUG = False

# instantiate the app
app = Flask(__name__)
api = Api(app)

# set config
app_settings = os.getenv('APP_SETTINGS')
app.config.from_object(app_settings)  
app.secret_key = os.urandom(24)
#load entire dataset into memory
#lookup = get_recipe_lookup(debug = DEBUG)
lookup = read_feather("/app/lookup_df.ftr")
#save to volume
lookup.to_feather("/app/lookup_df.ftr")
#data preprocessing
#construct favored
querystr = 'id < 71906 and review_count > 3000 or id > 90422 and review_count > 400'
favored = lookup.query(querystr)

# define API services

class Ping(Resource):
    def get(self):
        return {
        'message': 'pong!'
    }
api.add_resource(Ping, '/ping')

class Card(Resource):
    def get(self,recipe_id):
        #title,url,photo_url,rating_stars,review_count,cook_time_minutes,id
        return Response(lookup.query('id ==' + str(recipe_id)).to_json(orient="records"), mimetype='application/json')
    def post(self,title,url,photo_url,rating_stars,review_count,cook_time_minutes,id):
        pass
        #create recipe entry
        #save data to buffer file

api.add_resource(Card, '/recipecard/<int:recipe_id>/')

class Default(Resource):
    def get(self):
        NUMRESULTS = 30
        if len(favored) > NUMRESULTS:
            indices = list(range(len(favored)))
            random.shuffle(indices)
            indices = indices[:NUMRESULTS]
            return Response(favored.iloc[indices].to_json(orient="records"), mimetype='application/json')
        else:
            return jsonify(favored.to_dict())
api.add_resource(Default, '/default')

class Search(Resource):
    def get(self):
        NUMRESULTS = 30
        THRESHOLD = 80
        query = request.args.get('q')
        choices = lookup.loc[:,'title'].tolist()
        res = process.extract(query,choices,limit = NUMRESULTS,scorer=fuzz.partial_ratio)
        #[(title:str,percent match:double,id:int):tuple]:list

        #collect required information about card and output
        out = DataFrame()
        for _,percent_match,id in res:
            if percent_match > THRESHOLD:
                card = lookup.query('id ==' + str(id)).copy()
                card.loc[:,'percent_match'] = percent_match
                out = out.append(card)
        return Response(out.to_json(orient="records"), mimetype='application/json')
api.add_resource(Search, '/search')
class Recommend(Resource):
    def get(self):
        id = request.headers.get('Authorization') #assumes: id doesn't change

        return jsonify(id)
api.add_resource(Recommend, '/recommend')