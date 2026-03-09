// Do NOT change. Changes will be lost next time file is generated

#define R__DICTIONARY_FILENAME dItmpdIbdIjunodOihepdOacdOcndIel9_amd64_gcc11dIReleasedIJ25dO7dO1dItaoswdIbuilddIDataModeldIElecEventdIsrcdITvtElecEvtDict
#define R__NO_DEPRECATION

/*******************************************************************/
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#define G__DICTIONARY
#include "ROOT/RConfig.hxx"
#include "TClass.h"
#include "TDictAttributeMap.h"
#include "TInterpreter.h"
#include "TROOT.h"
#include "TBuffer.h"
#include "TMemberInspector.h"
#include "TInterpreter.h"
#include "TVirtualMutex.h"
#include "TError.h"

#ifndef G__ROOT
#define G__ROOT
#endif

#include "RtypesImp.h"
#include "TIsAProxy.h"
#include "TFileMergeInfo.h"
#include <algorithm>
#include "TCollectionProxyInfo.h"
/*******************************************************************/

#include "TDataMember.h"

// Header files passed as explicit arguments
#include "/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/ElecEvent/Event/TvtElecEvt.h"

// Header files passed via #pragma extra_include

// The generated code does not explicitly qualify STL entities
namespace std {} using namespace std;

namespace ROOT {
   static void *new_TaocLcLTvtElecEvt(void *p = nullptr);
   static void *newArray_TaocLcLTvtElecEvt(Long_t size, void *p);
   static void delete_TaocLcLTvtElecEvt(void *p);
   static void deleteArray_TaocLcLTvtElecEvt(void *p);
   static void destruct_TaocLcLTvtElecEvt(void *p);

   // Function generating the singleton type initializer
   static TGenericClassInfo *GenerateInitInstanceLocal(const ::Tao::TvtElecEvt*)
   {
      ::Tao::TvtElecEvt *ptr = nullptr;
      static ::TVirtualIsAProxy* isa_proxy = new ::TInstrumentedIsAProxy< ::Tao::TvtElecEvt >(nullptr);
      static ::ROOT::TGenericClassInfo 
         instance("Tao::TvtElecEvt", ::Tao::TvtElecEvt::Class_Version(), "Event/TvtElecEvt.h", 11,
                  typeid(::Tao::TvtElecEvt), ::ROOT::Internal::DefineBehavior(ptr, ptr),
                  &::Tao::TvtElecEvt::Dictionary, isa_proxy, 4,
                  sizeof(::Tao::TvtElecEvt) );
      instance.SetNew(&new_TaocLcLTvtElecEvt);
      instance.SetNewArray(&newArray_TaocLcLTvtElecEvt);
      instance.SetDelete(&delete_TaocLcLTvtElecEvt);
      instance.SetDeleteArray(&deleteArray_TaocLcLTvtElecEvt);
      instance.SetDestructor(&destruct_TaocLcLTvtElecEvt);
      return &instance;
   }
   TGenericClassInfo *GenerateInitInstance(const ::Tao::TvtElecEvt*)
   {
      return GenerateInitInstanceLocal(static_cast<::Tao::TvtElecEvt*>(nullptr));
   }
   // Static variable to force the class initialization
   static ::ROOT::TGenericClassInfo *_R__UNIQUE_DICT_(Init) = GenerateInitInstanceLocal(static_cast<const ::Tao::TvtElecEvt*>(nullptr)); R__UseDummy(_R__UNIQUE_DICT_(Init));
} // end of namespace ROOT

namespace Tao {
//______________________________________________________________________________
atomic_TClass_ptr TvtElecEvt::fgIsA(nullptr);  // static to hold class pointer

//______________________________________________________________________________
const char *TvtElecEvt::Class_Name()
{
   return "Tao::TvtElecEvt";
}

//______________________________________________________________________________
const char *TvtElecEvt::ImplFileName()
{
   return ::ROOT::GenerateInitInstanceLocal((const ::Tao::TvtElecEvt*)nullptr)->GetImplFileName();
}

//______________________________________________________________________________
int TvtElecEvt::ImplFileLine()
{
   return ::ROOT::GenerateInitInstanceLocal((const ::Tao::TvtElecEvt*)nullptr)->GetImplFileLine();
}

//______________________________________________________________________________
TClass *TvtElecEvt::Dictionary()
{
   fgIsA = ::ROOT::GenerateInitInstanceLocal((const ::Tao::TvtElecEvt*)nullptr)->GetClass();
   return fgIsA;
}

//______________________________________________________________________________
TClass *TvtElecEvt::Class()
{
   if (!fgIsA.load()) { R__LOCKGUARD(gInterpreterMutex); fgIsA = ::ROOT::GenerateInitInstanceLocal((const ::Tao::TvtElecEvt*)nullptr)->GetClass(); }
   return fgIsA;
}

} // namespace Tao
namespace Tao {
//______________________________________________________________________________
void TvtElecEvt::Streamer(TBuffer &R__b)
{
   // Stream an object of class Tao::TvtElecEvt.

   if (R__b.IsReading()) {
      R__b.ReadClassBuffer(Tao::TvtElecEvt::Class(),this);
   } else {
      R__b.WriteClassBuffer(Tao::TvtElecEvt::Class(),this);
   }
}

} // namespace Tao
namespace ROOT {
   // Wrappers around operator new
   static void *new_TaocLcLTvtElecEvt(void *p) {
      return  p ? new(p) ::Tao::TvtElecEvt : new ::Tao::TvtElecEvt;
   }
   static void *newArray_TaocLcLTvtElecEvt(Long_t nElements, void *p) {
      return p ? new(p) ::Tao::TvtElecEvt[nElements] : new ::Tao::TvtElecEvt[nElements];
   }
   // Wrapper around operator delete
   static void delete_TaocLcLTvtElecEvt(void *p) {
      delete (static_cast<::Tao::TvtElecEvt*>(p));
   }
   static void deleteArray_TaocLcLTvtElecEvt(void *p) {
      delete [] (static_cast<::Tao::TvtElecEvt*>(p));
   }
   static void destruct_TaocLcLTvtElecEvt(void *p) {
      typedef ::Tao::TvtElecEvt current_t;
      (static_cast<current_t*>(p))->~current_t();
   }
} // end of namespace ROOT for class ::Tao::TvtElecEvt

namespace ROOT {
   static TClass *vectorlETaocLcLTvtElecChannelgR_Dictionary();
   static void vectorlETaocLcLTvtElecChannelgR_TClassManip(TClass*);
   static void *new_vectorlETaocLcLTvtElecChannelgR(void *p = nullptr);
   static void *newArray_vectorlETaocLcLTvtElecChannelgR(Long_t size, void *p);
   static void delete_vectorlETaocLcLTvtElecChannelgR(void *p);
   static void deleteArray_vectorlETaocLcLTvtElecChannelgR(void *p);
   static void destruct_vectorlETaocLcLTvtElecChannelgR(void *p);

   // Function generating the singleton type initializer
   static TGenericClassInfo *GenerateInitInstanceLocal(const vector<Tao::TvtElecChannel>*)
   {
      vector<Tao::TvtElecChannel> *ptr = nullptr;
      static ::TVirtualIsAProxy* isa_proxy = new ::TIsAProxy(typeid(vector<Tao::TvtElecChannel>));
      static ::ROOT::TGenericClassInfo 
         instance("vector<Tao::TvtElecChannel>", -2, "vector", 389,
                  typeid(vector<Tao::TvtElecChannel>), ::ROOT::Internal::DefineBehavior(ptr, ptr),
                  &vectorlETaocLcLTvtElecChannelgR_Dictionary, isa_proxy, 0,
                  sizeof(vector<Tao::TvtElecChannel>) );
      instance.SetNew(&new_vectorlETaocLcLTvtElecChannelgR);
      instance.SetNewArray(&newArray_vectorlETaocLcLTvtElecChannelgR);
      instance.SetDelete(&delete_vectorlETaocLcLTvtElecChannelgR);
      instance.SetDeleteArray(&deleteArray_vectorlETaocLcLTvtElecChannelgR);
      instance.SetDestructor(&destruct_vectorlETaocLcLTvtElecChannelgR);
      instance.AdoptCollectionProxyInfo(TCollectionProxyInfo::Generate(TCollectionProxyInfo::Pushback< vector<Tao::TvtElecChannel> >()));

      instance.AdoptAlternate(::ROOT::AddClassAlternate("vector<Tao::TvtElecChannel>","std::vector<Tao::TvtElecChannel, std::allocator<Tao::TvtElecChannel> >"));
      return &instance;
   }
   // Static variable to force the class initialization
   static ::ROOT::TGenericClassInfo *_R__UNIQUE_DICT_(Init) = GenerateInitInstanceLocal(static_cast<const vector<Tao::TvtElecChannel>*>(nullptr)); R__UseDummy(_R__UNIQUE_DICT_(Init));

   // Dictionary for non-ClassDef classes
   static TClass *vectorlETaocLcLTvtElecChannelgR_Dictionary() {
      TClass* theClass =::ROOT::GenerateInitInstanceLocal(static_cast<const vector<Tao::TvtElecChannel>*>(nullptr))->GetClass();
      vectorlETaocLcLTvtElecChannelgR_TClassManip(theClass);
   return theClass;
   }

   static void vectorlETaocLcLTvtElecChannelgR_TClassManip(TClass* ){
   }

} // end of namespace ROOT

namespace ROOT {
   // Wrappers around operator new
   static void *new_vectorlETaocLcLTvtElecChannelgR(void *p) {
      return  p ? ::new(static_cast<::ROOT::Internal::TOperatorNewHelper*>(p)) vector<Tao::TvtElecChannel> : new vector<Tao::TvtElecChannel>;
   }
   static void *newArray_vectorlETaocLcLTvtElecChannelgR(Long_t nElements, void *p) {
      return p ? ::new(static_cast<::ROOT::Internal::TOperatorNewHelper*>(p)) vector<Tao::TvtElecChannel>[nElements] : new vector<Tao::TvtElecChannel>[nElements];
   }
   // Wrapper around operator delete
   static void delete_vectorlETaocLcLTvtElecChannelgR(void *p) {
      delete (static_cast<vector<Tao::TvtElecChannel>*>(p));
   }
   static void deleteArray_vectorlETaocLcLTvtElecChannelgR(void *p) {
      delete [] (static_cast<vector<Tao::TvtElecChannel>*>(p));
   }
   static void destruct_vectorlETaocLcLTvtElecChannelgR(void *p) {
      typedef vector<Tao::TvtElecChannel> current_t;
      (static_cast<current_t*>(p))->~current_t();
   }
} // end of namespace ROOT for class vector<Tao::TvtElecChannel>

namespace {
  void TriggerDictionaryInitialization_TvtElecEvtDict_Impl() {
    static const char* headers[] = {
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/ElecEvent/Event/TvtElecEvt.h",
nullptr
    };
    static const char* includePaths[] = {
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/build/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/Python/3.11.10/include/python3.11",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/Boost/1.85.0",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/log4cpp/1.1.3/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/ROOT/6.30.08/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/CLHEP/2.4.7.1/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J24.2.0/ExternalLibs/CLHEP/2.4.7.1/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/Geant4/10.04.p02.juno/include/geant4",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/HepMC/2.06.11/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/genie/3.04.02/include/GENIE",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/frontier/2.10.2/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/mysql-connector-c/6.1.9/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/mysql-connector-cpp/1.1.12/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/libyaml/0.2.4/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/libonnxruntime/1.17.3/include/onnxruntime",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/libonnxruntime/1.17.3/include/onnxruntime/core/session",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/nuwro/21.09.2/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/ElecEvent",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/ElecEvent/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/build/DataModel/ElecEvent",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/junosw/InstallArea/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/junosw/InstallArea/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/junosw/InstallArea/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.4.0/ExternalLibs/ROOT/6.30.08/include/",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/build/DataModel/ElecEvent/",
nullptr
    };
    static const char* fwdDeclCode = R"DICTFWDDCLS(
#line 1 "TvtElecEvtDict dictionary forward declarations' payload"
#pragma clang diagnostic ignored "-Wkeyword-compat"
#pragma clang diagnostic ignored "-Wignored-attributes"
#pragma clang diagnostic ignored "-Wreturn-type-c-linkage"
extern int __Cling_AutoLoading_Map;
namespace Tao{class __attribute__((annotate("$clingAutoload$/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/ElecEvent/Event/TvtElecEvt.h")))  TvtElecEvt;}
)DICTFWDDCLS";
    static const char* payloadCode = R"DICTPAYLOAD(
#line 1 "TvtElecEvtDict dictionary payload"


#define _BACKWARD_BACKWARD_WARNING_H
// Inline headers
#include "/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/ElecEvent/Event/TvtElecEvt.h"

#undef  _BACKWARD_BACKWARD_WARNING_H
)DICTPAYLOAD";
    static const char* classesHeaders[] = {
"Tao::TvtElecEvt", payloadCode, "@",
nullptr
};
    static bool isInitialized = false;
    if (!isInitialized) {
      TROOT::RegisterModule("TvtElecEvtDict",
        headers, includePaths, payloadCode, fwdDeclCode,
        TriggerDictionaryInitialization_TvtElecEvtDict_Impl, {}, classesHeaders, /*hasCxxModule*/false);
      isInitialized = true;
    }
  }
  static struct DictInit {
    DictInit() {
      TriggerDictionaryInitialization_TvtElecEvtDict_Impl();
    }
  } __TheDictionaryInitializer;
}
void TriggerDictionaryInitialization_TvtElecEvtDict() {
  TriggerDictionaryInitialization_TvtElecEvtDict_Impl();
}
