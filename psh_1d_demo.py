# -*- coding: utf-8 -*-
"""
Created on Mon Dec 18 14:29:06 2017

@author:
"""

import time
import numpy as np

def gcd(a, b):
	if a < b:
		a, b = b, a
	while b > 0:
		a, b = b, a % b
	return a

def popcnt(x):
	r = 0
	while x > 0:
		r += x & 1
		x >>= 1
	return r

def is_prime(x):
	if x == 2:
		return True
	if x == 1 or x & 1 == 0:
		return False
	y = int(x**.5) | 1
	while y > 1:
		if x % y == 0:
			return False
		y -= 2
	return True

def universal_hash(key, size, a = 31, b = 53, p = 1234567891):
	return ((key * a + b) % p) % size

def make_universal_hash(max_key = 65535, p = 1234567891):
	a = np.random.randint(0, p // (1 + max_key))
	b = np.random.randint(0, p)
	f = lambda key, size: universal_hash(key, size, a, b, p)
	f.a, f.b, f.p = a, b, p
	return f

#def universal_hash(key, size, mat = np.random.randint(0, 2147483648, 31)):
#	r = 0
#	for m in mat:
#		r = (r << 1) | (popcnt(m & key) & 1)
#	return r % size
#
#def make_universal_hash(bits = 24):
#	mat = np.random.randint(0, 2 ** bits, bits)
#	f = lambda key, size: universal_hash(key, size, mat)
#	f.mat = mat
#	return f
	
class BadHashFuncException(BaseException):
	pass
	
class BadOffsetTableSizeException(BaseException):
	pass
	
class BadBucketSizeException(BaseException):
	pass

def generateRandomData(dataSize, maxKey = 88888888):
	data = []
	dmap = {}
	while len(data) < dataSize:
		d = np.random.randint(0, maxKey)
		if not d in dmap:
			dmap[d] = 1
			data.append(d)
	return data

dataSize = 200 * 1000
#data = np.ogrid[:dataSize]
#data = (data ** 1.5).astype(np.uint)
#maxKey = data[-1]
maxKey = 88888888
data = generateRandomData(dataSize)
testData = generateRandomData(dataSize)
print("Data generated, density: {}".format(dataSize / maxKey))
hashFuncAttempts = int(np.log2(dataSize))
extendedRatio = 1.1

offsetTableSize = int(dataSize * extendedRatio) | 1
tryNewOffsetTableSize = True
while tryNewOffsetTableSize:
	tryNewOffsetTableSize = False
	
	while not is_prime(offsetTableSize):
		offsetTableSize += 2

	retriesHashFunc = 0
	tryNewHashFunc = True
	while tryNewHashFunc:
		tryNewHashFunc = False
		
		maxOffsetBucketCount = dataSize
		bestHashFunc = make_universal_hash()
		offsetBucketCounts = np.zeros((offsetTableSize), dtype = np.uint)
		for attempt in range(hashFuncAttempts):
			hashFunc = make_universal_hash()
			offsetBucketCounts.fill(0)
			for d in data:
				h = hashFunc(d, offsetTableSize)
				offsetBucketCounts[h] += 1
			currentMaxCount = np.max(offsetBucketCounts)
			if maxOffsetBucketCount > currentMaxCount:
				maxOffsetBucketCount = currentMaxCount
				bestHashFunc = hashFunc
		print("Max bucket size: {} for offset table size {}"
			.format(maxOffsetBucketCount, offsetTableSize))

		offsetBucket = [[] for i in range(offsetTableSize)]
		for d in data:
			h = hashFunc(d, offsetTableSize)
			offsetBucket[h].append(d)
			
		try:
			desiredValueTableSize = 4 * offsetTableSize
			offsetTable = np.zeros((offsetTableSize + 1), dtype = np.uint)
			valueTable = np.zeros((desiredValueTableSize), dtype = np.uint)
			offset = 0
			retriesBucketSize = 0
			for h, bucket in enumerate(offsetBucket):
				if offset >= desiredValueTableSize:
					raise BadHashFuncException()
					
				offsetTable[h] = offset
				bucketSize = len(bucket)
				if bucketSize == 1:
					valueTable[offset] = bucket[0]
				else:
					bucketSize = int((bucketSize * extendedRatio) ** 2) | 1
					
					tryNewBucketSize = True
					while tryNewBucketSize:
						tryNewBucketSize = False
						
						while not is_prime(bucketSize):
							bucketSize += 2	
						if offset + bucketSize > desiredValueTableSize:
							raise BadHashFuncException()
							
						try:
							counts = np.zeros((bucketSize), dtype = np.uint)
							for d in bucket:
								h = hashFunc(d, bucketSize)
								if counts[h] == 0:
									counts[h] = 1
								else:
									raise BadBucketSizeException()
						except BadBucketSizeException:
							tryNewBucketSize = True
							retriesBucketSize += 1
							bucketSize += 2
					for d in bucket:
						h = hashFunc(d, bucketSize)
						valueTable[offset + h] = d
				offset += bucketSize
			offsetTable[offsetTableSize] = offset
			valueTable = valueTable[:offset]
			print("Hash {} retries, bucket {} retries: {}/{}"
				.format(retriesHashFunc, retriesBucketSize, offset, desiredValueTableSize))
			print("Density: {} + {} = {}"
				.format(offset / maxKey, offsetTableSize / maxKey, (offset + offsetTableSize) / maxKey))
		except BadHashFuncException:
			tryNewHashFunc = True
			retriesHashFunc += 1	

def test(d):
	h = hashFunc(d, offsetTableSize)
	offset = offsetTable[h]
	size = offsetTable[h + 1] - offset
	return valueTable[offset + hashFunc(d, size)] == d

def hashMapTest(data, testData):
	dmap = {}
	for d in data:
		dmap[d] = 1
		
	time0 = time.time()
	cnt = 0
	for d in testData:
		if d in dmap:
			cnt += 1
	time1 = time.time()
	
	print("Hash map test: hit = {}, time = {}".format(cnt, time1 - time0))
	
def pshTest(data, testData):
	time0 = time.time()
	cnt = 0
	for d in testData:
		if test(d):
			cnt += 1
	time1 = time.time()
	
	print("PSH test: hit = {}, time = {}".format(cnt, time1 - time0))
	
def makeTableView(table):
	width = int(table.shape[0]**.5)+1
	img = np.zeros((width * width), dtype = table.dtype)
	img[:table.shape[0]] = table
	return img.reshape((width, width))

def visualizeTables():
	import matplotlib.pyplot as plt
	plt.figure()
	plt.subplot(121, title = "Value Table {}".format(valueTable.shape))
	plt.imshow(makeTableView(valueTable))
	plt.subplot(122, title = "Offset Table {}".format(offsetTable.shape))
	plt.imshow(makeTableView(offsetTable))
	
	
hashMapTest(data, testData)
pshTest(data, testData)
visualizeTables()
